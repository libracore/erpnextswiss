"""Synthetic bank-file boundary tests; no Frappe site, credentials or financial data."""

from dataclasses import FrozenInstanceError
from hashlib import sha256
from io import BytesIO
import stat
import struct
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
import zlib

from lxml import etree

from erpnextswiss.scripts import bank_file_admission as admission


PROFILE = "camt.053.001.08"


def xml(profile=PROFILE, currency="CHF", entries=False, multiple=False):
    statement = profile == PROFILE
    body = "BkToCstmrStmt" if statement else "BkToCstmrDbtCdtNtfctn"
    unit = "Stmt" if statement else "Ntfctn"
    account = "<Acct><Id><IBAN>CH9300762011623852957</IBAN></Id><Ccy>" + currency + "</Ccy></Acct>"
    balance = ("<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp><Amt Ccy=\"" + currency
               + "\">1234.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2026-09-12</Dt></Dt></Bal>")
    entry = ("<Ntry><Amt Ccy=\"" + currency + "\">12.34000</Amt><CdtDbtInd>CRDT</CdtDbtInd>"
             "<Sts><Cd>BOOK</Cd></Sts><BookgDt><Dt>2026-09-12</Dt></BookgDt>"
             "<BkTxCd><Prtry><Cd>TEST</Cd></Prtry></BkTxCd></Ntry>")
    row = "<" + unit + "><Id>statement-1</Id>" + account + (balance if statement else "")
    row += (entry if entries else "") + "</" + unit + ">"
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?><Document xmlns=\""
            "urn:iso:std:iso:20022:tech:xsd:" + profile + "\"><" + body + ">"
            "<GrpHdr><MsgId>synthetic-test</MsgId><CreDtTm>2026-09-12T10:00:00Z</CreDtTm>"
            "</GrpHdr>" + row * (2 if multiple else 1) + "</" + body + "></Document>").encode()


def zipped(files=None, compression=ZIP_DEFLATED, comment=b""):
    output = BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(output, "w", compression=compression) as archive:
            for name, content in files if files is not None else [("statement.xml", xml())]:
                archive.writestr(name, content)
            archive.comment = comment
    return output.getvalue()


def end_record(payload, **values):
    fields = ["signature", "disk", "directory_disk", "disk_count", "count", "size", "offset", "comment_size"]
    position = payload.rfind(b"PK\x05\x06")
    current = dict(zip(fields, admission._EOCD.unpack_from(payload, position)))
    current.update(values)
    return payload[:position] + admission._EOCD.pack(*(current[name] for name in fields)) + payload[position + 22:]


class TestBankFileAdmission(unittest.TestCase):
    def test_existing_schemas_cover_both_profiles_currencies_and_balance_only(self):
        for profile in admission.PROFILES:
            for currency in ("CHF", "EUR"):
                for entries in (False, True):
                    with self.subTest(profile=profile, currency=currency, entries=entries):
                        content = xml(profile, currency, entries, multiple=True)
                        payload = zipped([("bank.xml", content)])
                        result = admission.read_bank_archive(payload, profile)
                        self.assertEqual(result.sha256, sha256(payload).hexdigest())
                        self.assertEqual(result.files[0].sha256, sha256(content).hexdigest())
                        self.assertEqual(result.files[0].content, content)
                        self.assertNotIn("CH9300762011623852957", repr(result))
                        self.assertNotIn("bank.xml", repr(result))
                        with self.assertRaises(FrozenInstanceError):
                            result.profile = "changed"

    def test_prefixes_utf16_comments_and_builtin_escapes_preserve_bytes(self):
        for encoding in ("UTF-8", "UTF-16"):
            source = xml().replace(b"synthetic-test", b"test &amp; other")
            root = etree.fromstring(source)
            namespaced = etree.Element(root.tag, nsmap={"bank": root.nsmap[None]})
            namespaced.extend(root)
            content = etree.tostring(namespaced, encoding=encoding, xml_declaration=True)
            result = admission.read_bank_archive(zipped([("konto.XML", content)]), PROFILE)
            self.assertEqual(result.files[0].content, content)

    def test_multiple_files_keep_order_and_paths_without_extracting(self):
        first, second = xml(), xml(currency="EUR", entries=True)
        payload = zipped([("daily/", b""), ("daily/one.xml", first), ("daily/two.xml", second)], comment=b"bank archive")
        with patch.object(ZipFile, "extract", side_effect=AssertionError("No disk extraction")), \
                patch.object(ZipFile, "extractall", side_effect=AssertionError("No disk extraction")):
            result = admission.read_bank_archive(payload, PROFILE)
        self.assertEqual([(f.name, f.content) for f in result.files], [("daily/one.xml", first), ("daily/two.xml", second)])

    def test_profile_and_type_fail_before_zip_open(self):
        for payload, profile in [(b"", PROFILE), ("not-bytes", PROFILE), (b"x", "../schema"), (b"x", None)]:
            with self.subTest(profile=profile), patch.object(admission, "ZipFile") as opened:
                with self.assertRaises(admission.BankFileError):
                    admission.read_bank_archive(payload, profile)
                opened.assert_not_called()

    def test_raw_archive_limit_and_exact_boundary(self):
        payload = zipped()
        with patch.object(admission, "MAX_ARCHIVE_BYTES", len(payload)):
            self.assertEqual(len(admission.read_bank_archive(payload, PROFILE).files), 1)
        with patch.object(admission, "MAX_ARCHIVE_BYTES", len(payload) - 1), patch.object(admission, "ZipFile") as opened:
            with self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(payload, PROFILE)
            opened.assert_not_called()

    def test_directory_budgets_checked_before_native_metadata_allocation(self):
        payload = zipped()
        cases = [end_record(payload, count=65, disk_count=65), end_record(payload, size=262145),
                 end_record(payload, disk=1), end_record(payload, directory_disk=1),
                 end_record(payload, count=65535), end_record(payload, offset=0),
                 payload[:-1], payload + b"trailing", b"MZ" + payload, zipped([])]
        for content in cases:
            with self.subTest(size=len(content)), patch.object(admission, "ZipFile") as opened:
                with self.assertRaises(admission.BankFileError):
                    admission.read_bank_archive(content, PROFILE)
                opened.assert_not_called()

    def test_actual_member_count_must_match_declaration(self):
        payload = zipped([("one.xml", xml()), ("two.xml", xml())])
        with self.assertRaisesRegex(admission.BankFileError, "member count"):
            admission.read_bank_archive(end_record(payload, count=1, disk_count=1), PROFILE)

    def test_64_members_accepted_65_rejected(self):
        files = [(str(index) + ".xml", xml()) for index in range(64)]
        self.assertEqual(len(admission.read_bank_archive(zipped(files), PROFILE).files), 64)
        with self.assertRaises(admission.BankFileError):
            admission.read_bank_archive(zipped(files + [("extra.xml", xml())]), PROFILE)

    def test_unsafe_names_rejected_not_sanitized(self):
        names = ["/bank.xml", "../bank.xml", "day/../bank.xml", "day//bank.xml", "./bank.xml",
                 "C:/bank.xml", "https://bank.xml", "day./bank.xml", "day /bank.xml",
                 "bad\n.xml", "a" * 252 + ".xml", "bank\u202e.xml"]
        for name in names:
            with self.subTest(name=name), self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(zipped([(name, xml())]), PROFILE)

    def test_backslash_in_raw_zip_name_is_rejected_on_every_platform(self):
        # Windows ZipInfo normalizes backslashes while writing: alter both headers.
        payload = zipped([("dayXbank.xml", xml())]).replace(b"dayXbank.xml", b"day\\bank.xml")
        with self.assertRaises(admission.BankFileError):
            admission.read_bank_archive(payload, PROFILE)

    def test_nul_name_in_original_zip_header_rejected(self):
        payload = zipped([("badX.xml", xml())]).replace(b"badX.xml", b"bad\0.xml")
        with self.assertRaises(admission.BankFileError):
            admission.read_bank_archive(payload, PROFILE)

    def test_duplicate_case_and_unicode_equivalent_names_rejected(self):
        for names in [("bank.xml", "bank.xml"), ("BANK.xml", "bank.xml"), ("\u00e9.xml", "e\u0301.xml")]:
            with self.subTest(names=names), self.assertRaisesRegex(admission.BankFileError, "duplicate"):
                admission.read_bank_archive(zipped([(name, xml()) for name in names]), PROFILE)

    def test_directory_only_nonxml_and_nested_archive_are_rejected(self):
        for files in [[("day/", b"")], [("day/", xml())], [("bank.txt", xml())], [("nested.zip", zipped())]]:
            with self.subTest(name=files[0][0]), self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(zipped(files), PROFILE)

    def test_links_devices_and_unsupported_compression_are_rejected(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFDIR):
            info = ZipInfo("bank.xml")
            info.create_system = 3
            info.external_attr = (kind | 0o600) << 16
            with self.subTest(kind=kind), self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(zipped([(info, xml())]), PROFILE)
        with self.assertRaises(admission.BankFileError):
            admission.read_bank_archive(zipped(compression=ZIP_BZIP2), PROFILE)

    def test_encrypted_archive_rejected_before_member_read(self):
        payload = bytearray(zipped())
        central = payload.index(b"PK\x01\x02")
        struct.pack_into("<H", payload, central + 8, 1)
        with patch.object(ZipFile, "open") as opened, self.assertRaises(admission.BankFileError):
            admission.read_bank_archive(bytes(payload), PROFILE)
        opened.assert_not_called()

    def test_crc_corruption_and_header_name_mismatch_rejected(self):
        payload = zipped(compression=ZIP_STORED)
        corrupted = payload.replace(b"synthetic-test", b"synthetic-fail", 1)
        mismatch = payload.replace(b"statement.xml", b"different.xml", 1)
        for content in (corrupted, mismatch):
            with self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(content, PROFILE)

    def test_false_short_size_and_crc_cannot_hide_additional_xml_content(self):
        content = xml()
        for compression in (ZIP_STORED, ZIP_DEFLATED):
            payload = bytearray(zipped([("bank.xml", content + b"<hidden/>")], compression))
            central = payload.index(b"PK\x01\x02")
            # A native ZipExtFile can silently truncate to the claimed file_size.
            # Forge matching CRCs for that valid prefix, not the actual whole entry.
            for offset in (14, central + 16):
                struct.pack_into("<L", payload, offset, zlib.crc32(content))
            for offset in (22, central + 24):
                struct.pack_into("<L", payload, offset, len(content))
            with ZipFile(BytesIO(payload)) as native:
                self.assertEqual(native.read("bank.xml"), content)
            with self.subTest(compression=compression), self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(bytes(payload), PROFILE)

    def test_local_zip64_and_streaming_data_descriptors_remain_compatible(self):
        output = BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            with archive.open("bank.xml", "w", force_zip64=True) as stream:
                stream.write(xml())
        self.assertEqual(admission.read_bank_archive(output.getvalue(), PROFILE).files[0].content, xml())

        class Unseekable(BytesIO):
            def seek(self, *args):
                raise OSError("streaming output")

        output = Unseekable()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("bank.xml", xml())
        self.assertEqual(admission.read_bank_archive(output.getvalue(), PROFILE).files[0].content, xml())

    def test_truncated_or_trailing_deflate_stream_rejected(self):
        payload = zipped()
        central = payload.index(b"PK\x01\x02")
        size = struct.unpack_from("<L", payload, central + 20)[0]
        for delta in (-1, 1):
            altered = bytearray(payload)
            struct.pack_into("<L", altered, central + 20, size + delta)
            with self.subTest(delta=delta), self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(bytes(altered), PROFILE)

    def test_forged_expansion_stops_at_output_bound(self):
        output = BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            with archive.open("bank.xml", "w") as stream:
                for _ in range(64):
                    stream.write(b"x" * 1024 * 1024)
        payload = bytearray(output.getvalue())
        central = payload.index(b"PK\x01\x02")
        for offset in (22, central + 24):
            struct.pack_into("<L", payload, offset, admission.MAX_FILE_BYTES)
        with self.assertRaisesRegex(admission.BankFileError, "exceeds declared stream"):
            admission.read_bank_archive(bytes(payload), PROFILE)

    def test_size_and_expansion_budgets_precede_member_decompression(self):
        content = xml()
        payload = zipped([("one.xml", content), ("two.xml", content)])
        for limits in [{"MAX_FILE_BYTES": len(content) - 1}, {"MAX_TOTAL_BYTES": 2 * len(content) - 1}]:
            with patch.multiple(admission, **limits), patch.object(ZipFile, "open") as opened:
                with self.assertRaises(admission.BankFileError):
                    admission.read_bank_archive(payload, PROFILE)
                opened.assert_not_called()
        with patch.multiple(admission, MAX_FILE_BYTES=len(content), MAX_TOTAL_BYTES=2 * len(content)):
            self.assertEqual(len(admission.read_bank_archive(payload, PROFILE).files), 2)

    def test_late_invalid_member_returns_no_partial_files(self):
        with self.assertRaises(admission.BankFileError):
            admission.read_bank_archive(zipped([("one.xml", xml()), ("two.xml", b"<broken")]), PROFILE)

    def test_dtd_external_entities_and_utf16_do_not_resolve_resources(self):
        for declaration in [b'<!DOCTYPE Document [<!ENTITY e SYSTEM "file:///synthetic-private">]>',
                            b'<!DOCTYPE Document SYSTEM "https://example.invalid/schema">',
                            b'<!DOCTYPE Document [<!ENTITY e "expanded">]>']:
            content = xml().replace(b"?><Document", b"?>" + declaration + b"<Document")
            for encoding in ("utf-8", "utf-16"):
                encoded = content.replace(b'encoding="UTF-8"', ('encoding="' + encoding + '"').encode()).decode().encode(encoding)
                with patch.object(admission._NoExternalResources, "resolve") as resolver:
                    with self.assertRaises(admission.BankFileError) as error:
                        admission.validate_camt_xml(encoded, PROFILE)
                    resolver.assert_not_called()
                    self.assertNotIn("synthetic-private", str(error.exception))

    def test_schema_location_is_not_followed_and_schema_is_packaged(self):
        content = xml().replace(b"><BkToCstmrStmt", b' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                               b'xsi:schemaLocation="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08 '
                               b'https://example.invalid/evil.xsd"><BkToCstmrStmt')
        admission._schema.cache_clear()
        with patch.object(admission._NoExternalResources, "resolve") as resolver:
            admission.validate_camt_xml(content, PROFILE)
            resolver.assert_not_called()

    def test_wrong_root_namespace_version_mixed_profile_and_schema_types_rejected(self):
        for content in [b"<Document/>", xml("camt.054.001.08"), xml().replace(b"001.08", b"001.02"),
                        xml().replace(b"1234.00", b"not-money"), xml().replace(b"2026-09-12T10:00:00Z", b"not-date"),
                        xml().replace(b"</Document>", b"<extra/></Document>"), xml() + b"<extra/>",
                        xml().replace(b"<Stmt>", b"<Stmt><unexpected/>")]:
            with self.subTest(size=len(content)), self.assertRaises(admission.BankFileError):
                admission.validate_camt_xml(content, PROFILE)

    def test_xml_structural_limits_before_schema_dom(self):
        count = sum(1 for _ in etree.fromstring(xml()).iter())
        with patch.object(admission, "MAX_XML_ELEMENTS", count):
            admission.validate_camt_xml(xml(), PROFILE)
        for limit in [{"MAX_XML_ELEMENTS": count - 1}, {"MAX_XML_DEPTH": 3}, {"MAX_XML_ATTRIBUTES": 0}]:
            with patch.multiple(admission, **limit), patch.object(admission, "_schema") as schema:
                with self.assertRaisesRegex(admission.BankFileError, "structure"):
                    admission.validate_camt_xml(xml(), PROFILE)
                schema.assert_not_called()

    def test_error_and_repr_do_not_include_file_or_account_data(self):
        payload = zipped([("private-account.xml", b"<private-bank-record>SECRET")])
        with self.assertRaises(admission.BankFileError) as error:
            admission.read_bank_archive(payload, PROFILE)
        for secret in ("SECRET", "private-account", "private-bank-record"):
            self.assertNotIn(secret, str(error.exception))

    def test_real_maximum_xml_and_total_archive_boundary(self):
        base = xml()
        padding = b"<!--" + b" " * (admission.MAX_FILE_BYTES - len(base) - 7) + b"-->"
        maximum = base.replace(b"</Document>", padding + b"</Document>")
        self.assertEqual(len(maximum), admission.MAX_FILE_BYTES)
        payload = zipped([(str(i) + ".xml", maximum) for i in range(4)])
        result = admission.read_bank_archive(payload, PROFILE)
        self.assertEqual(sum(len(f.content) for f in result.files), admission.MAX_TOTAL_BYTES)
        self.assertTrue(all(f.content == maximum for f in result.files))
        for files in [[("too-large.xml", maximum + b" ")], [(str(i) + ".xml", maximum) for i in range(5)]]:
            with self.assertRaises(admission.BankFileError):
                admission.read_bank_archive(zipped(files), PROFILE)


if __name__ == "__main__":
    unittest.main()
