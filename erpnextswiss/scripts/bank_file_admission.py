"""Read-only bank file admission; no account matching, ERP writes or bank calls.

This is a boundary for the bank adapter, not a replacement for existing imports.
The caller must retain the encrypted original and enforce trusted account access.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import stat
import struct
import unicodedata
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile
import zlib

from lxml import etree


MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_MEMBERS = 64
MAX_DIRECTORY_BYTES = 256 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_XML_ELEMENTS = 100000
MAX_XML_DEPTH = 64
MAX_XML_ATTRIBUTES = 128
PROFILES = {
    "camt.053.001.08": "BkToCstmrStmt",
    "camt.054.001.08": "BkToCstmrDbtCdtNtfctn",
}
_EOCD = struct.Struct("<4s4H2LH")
_LOCAL_HEADER = struct.Struct("<4s5H3L2H")


class BankFileError(ValueError):
    """Sanitized admission failure; never include bank contents or file names."""


@dataclass(frozen=True)
class CamtFile:
    name: str = field(repr=False)
    content: bytes = field(repr=False)
    sha256: str


@dataclass(frozen=True)
class BankArchive:
    profile: str
    sha256: str
    files: tuple[CamtFile, ...]


def _profile(profile):
    if not isinstance(profile, str) or profile not in PROFILES:
        raise BankFileError("Unsupported bank file profile")
    return "{urn:iso:std:iso:20022:tech:xsd:" + profile + "}"


class _NoExternalResources(etree.Resolver):
    def resolve(self, url, public_id, context):
        raise BankFileError("External XML resources are forbidden")


class _XmlBudget:
    def __init__(self, profile):
        self.namespace = _profile(profile)
        self.body = self.namespace + PROFILES[profile]
        self.depth = self.elements = self.bodies = 0

    def start(self, tag, attributes):
        self.depth += 1
        self.elements += 1
        if (self.depth > MAX_XML_DEPTH or self.elements > MAX_XML_ELEMENTS
                or len(attributes) > MAX_XML_ATTRIBUTES):
            raise BankFileError("XML structure exceeds bank file limits")
        if self.depth == 1 and tag != self.namespace + "Document":
            raise BankFileError("XML profile does not match the requested bank file")
        if self.depth == 2:
            self.bodies += 1
            if tag != self.body or self.bodies != 1:
                raise BankFileError("Unexpected bank document envelope")

    def end(self, tag):
        self.depth -= 1

    def doctype(self, name, public_id, system_id):
        raise BankFileError("XML document types are forbidden")

    def close(self):
        return None


def _parser(target=None):
    parser = etree.XMLParser(target=target, resolve_entities=False, load_dtd=False,
                             no_network=True, recover=False, huge_tree=False)
    parser.resolvers.add(_NoExternalResources())
    return parser


@lru_cache(maxsize=2)
def _schema(profile):
    _profile(profile)
    # Use only the existing packaged schema, never a document's schemaLocation.
    path = Path(__file__).resolve().parents[1] / "public" / "xsd" / (profile + ".xsd")
    return etree.XMLSchema(etree.fromstring(path.read_bytes(), _parser()))


def validate_camt_xml(content: bytes, profile: str) -> None:
    """Validate bytes and the existing XSD without normalizing or mapping money."""
    _profile(profile)
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_FILE_BYTES:
        raise BankFileError("Bank XML size is outside limits")
    try:
        # The event-only pass bounds the tree before schema validation allocates it.
        etree.fromstring(content, _parser(_XmlBudget(profile)))
        document = etree.fromstring(content, _parser())
        if not _schema(profile).validate(document):
            raise BankFileError("Bank XML does not satisfy the requested schema")
    except etree.LxmlError:
        raise BankFileError("Invalid bank XML or packaged schema") from None


def _directory_budget(payload):
    # Bound central-directory allocation BEFORE ZipFile creates all ZipInfo objects.
    # Only the fixed classic ZIP end record is inspected here; zipfile remains the
    # archive parser/decoder. ZIP64 end records and split/SFX archives are not admitted.
    position = payload.rfind(b"PK\x05\x06", max(0, len(payload) - 65557))
    if position < 0 or position + _EOCD.size > len(payload):
        raise BankFileError("Missing ZIP directory")
    _, disk, directory_disk, disk_count, count, size, offset, comment_size = _EOCD.unpack_from(payload, position)
    if (disk or directory_disk or disk_count != count or not 0 < count <= MAX_MEMBERS
            or not 0 < size <= MAX_DIRECTORY_BYTES or offset + size != position
            or position + _EOCD.size + comment_size != len(payload)
            or not payload.startswith(b"PK\x03\x04")):
        raise BankFileError("Unsupported or oversized ZIP directory")
    return count


def _member_name(info):
    name = info.orig_filename
    if (not name or len(name.encode("utf-8")) > 255 or name != info.filename
            or "\\" in name or ":" in name
            or any(unicodedata.category(char).startswith("C") for char in name)):
        raise BankFileError("Unsafe ZIP member name")
    parts = (name[:-1] if info.is_dir() else name).split("/")
    if any(part in {"", ".", ".."} or part.endswith((" ", ".")) for part in parts):
        raise BankFileError("Unsafe ZIP member path")
    return unicodedata.normalize("NFC", name.rstrip("/")).casefold()


def _complete_member(payload, info):
    # ZipFile.open has checked the member/header/range. ZipExtFile.read alone can
    # truncate to a forged file_size with a matching prefix CRC. Use native zlib
    # with a hard output bound and require its actual EOF, full size and CRC.
    header = _LOCAL_HEADER.unpack_from(payload, info.header_offset)
    if header[0] != b"PK\x03\x04" or header[2] != info.flag_bits or header[3] != info.compress_type:
        raise BankFileError("Inconsistent local ZIP header")
    start = info.header_offset + _LOCAL_HEADER.size + header[-2] + header[-1]
    end = start + info.compress_size
    if end > len(payload):
        raise BankFileError("Truncated ZIP member")
    if info.compress_type == ZIP_STORED:
        if info.compress_size != info.file_size:
            raise BankFileError("Stored ZIP member length differs from metadata")
        content = payload[start:end]
    else:
        decoder = zlib.decompressobj(-zlib.MAX_WBITS)
        chunks = []
        size = 0
        for offset in range(start, end, 65536):
            chunk = decoder.decompress(memoryview(payload)[offset:min(offset + 65536, end)], info.file_size - size + 1)
            size += len(chunk)
            if size > info.file_size or decoder.unconsumed_tail or decoder.unused_data:
                raise BankFileError("Deflated ZIP member exceeds declared stream")
            chunks.append(chunk)
        if not decoder.eof or size != info.file_size:
            raise BankFileError("Incomplete deflated ZIP member")
        content = b"".join(chunks)
    if zlib.crc32(content) != info.CRC:
        raise BankFileError("ZIP member integrity failed")
    return content


def read_bank_archive(payload: bytes, profile: str) -> BankArchive:
    """Admit an entire ZIP atomically; return byte-exact XML files, never extract.

    This proves format safety only, not permission, IBAN ownership, duplicate
    business transactions or approval to book. An invalid later member returns no
    partial result. No generator/callback can write early members along the way.
    """
    _profile(profile)
    if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_ARCHIVE_BYTES:
        raise BankFileError("Bank archive size is outside limits")
    count = _directory_budget(payload)
    try:
        with ZipFile(BytesIO(payload), "r") as archive:
            members = archive.infolist()
            if len(members) != count:
                raise BankFileError("Inconsistent ZIP member count")
            names = set()
            total = 0
            for info in members:
                name = _member_name(info)
                if name in names:
                    raise BankFileError("Ambiguous duplicate ZIP member")
                names.add(name)
                kind = stat.S_IFMT(info.external_attr >> 16) if info.create_system == 3 else 0
                if (kind not in {0, stat.S_IFREG, stat.S_IFDIR}
                        or kind == stat.S_IFDIR and not info.is_dir()
                        or info.flag_bits & (1 | 32 | 64)
                        or info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}):
                    raise BankFileError("Unsupported ZIP member type or encoding")
                if info.is_dir():
                    if info.file_size != 0:
                        raise BankFileError("Nonempty ZIP directory member")
                elif not name.endswith(".xml") or not 0 < info.file_size <= MAX_FILE_BYTES:
                    raise BankFileError("Bank ZIP must contain bounded XML files")
                if not 0 <= info.compress_size <= MAX_ARCHIVE_BYTES:
                    raise BankFileError("Compressed ZIP member exceeds limits")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise BankFileError("Expanded bank archive exceeds limits")
            files = []
            for info in members:
                with archive.open(info, "r"):
                    content = _complete_member(payload, info)
                if not info.is_dir():
                    validate_camt_xml(content, profile)
                    files.append(CamtFile(info.filename, content, sha256(content).hexdigest()))
            if not files:
                raise BankFileError("Bank ZIP contains no XML documents")
            return BankArchive(profile, sha256(payload).hexdigest(), tuple(files))
    except (BadZipFile, NotImplementedError, RuntimeError, EOFError, zlib.error, UnicodeError, struct.error):
        raise BankFileError("Invalid bank ZIP encoding or integrity") from None
