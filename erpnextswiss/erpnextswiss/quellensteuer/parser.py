import hashlib
import io
import re
import zipfile
from collections import Counter
from datetime import date

from frappe import _

FILE_PATTERN = re.compile(r"(?:^|/)tar(\d{2})([a-z]{2})\.txt$", re.IGNORECASE)
DATA_RECORDS = ("06", "11", "12", "13")
RATE_RECORDS = ("06", "11")


class TariffFileError(Exception):
    pass


def iter_tariff_files(content, cantons=None):
    """Yield (canton, text) for every ESTV tariff file in a (nested) zip archive."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for info in archive.infolist():
            if info.filename.lower().endswith(".zip"):
                yield from iter_tariff_files(archive.read(info), cantons)
                continue
            match = FILE_PATTERN.search(info.filename)
            if match and (not cantons or match.group(2).upper() in cantons):
                yield match.group(2).upper(), archive.read(info).decode("latin-1")


def to_date(value):
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))


def to_amount(value):
    return int(value) / 100 if value.strip() else 0.0


def to_row(line):
    """One rate row of an ESTV tariff file."""
    return {
        "record_type": line[0:2],
        "code": line[6:16].strip(),
        "valid_from": to_date(line[16:24]),
        "income_from": to_amount(line[24:33]),
        "step": to_amount(line[33:42]),
        "children": int(line[43:45].strip() or 0),
        "min_tax": to_amount(line[45:54]),
        "rate": to_amount(line[54:59]),
    }


def code_rows(text, code):
    """Rate rows of a single tariff code; the rows of all other codes are skipped."""
    for line in text.splitlines():
        if line[0:2] in RATE_RECORDS and line[6:16].strip() == code:
            yield to_row(line)


def parse(text):
    """Parse one ESTV tariff file (record format D_DVS 0005); rate rows are read later per code."""
    lines = [line.rstrip("\r\n") for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].startswith("00") or not lines[-1].startswith("99"):
        raise TariffFileError(_("Header or trailer record missing"))
    canton, trailer = lines[0][2:4], lines[-1]
    if trailer[17:19] != canton:
        raise TariffFileError(_("Trailer canton {0} does not match {1}").format(trailer[17:19], canton))
    if int(trailer[19:27]) != len(lines):
        raise TariffFileError(_("{0}: trailer announces {1} records, found {2}").format(canton, int(trailer[19:27]), len(lines)))
    codes, data_lines, valid_from = Counter(), [], None
    extra = {"commission": {}, "median_value": 0}
    for number, line in enumerate(lines[1:-1], start=2):
        record_type, code = line[0:2], line[6:16].strip()
        if record_type not in DATA_RECORDS or line[4:6] != canton:
            raise TariffFileError(_("{0}: invalid record in line {1}").format(canton, number))
        if line[2:4] != "01":
            raise TariffFileError(_("{0}: transaction type {1} in line {2} is not supported").format(canton, line[2:4], number))
        data_lines.append(line)
        if record_type == "12":
            extra["commission"][code] = to_amount(line[54:59])
        elif record_type == "13":
            extra["median_value"] = to_amount(line[45:54])
        else:
            codes[code] += 1
            valid_from = min(valid_from, line[16:24]) if valid_from else line[16:24]
    if not codes:
        raise TariffFileError(_("{0}: no tariff records").format(canton))
    return {
        "canton": canton,
        "creation_date": to_date(lines[0][19:27]),
        "header_text": " ".join(lines[0][27:107].split()),
        "record_count": len(lines),
        "valid_from": to_date(valid_from),
        "content_hash": hashlib.sha256("\n".join(sorted(data_lines)).encode()).hexdigest(),
        "codes": dict(codes),
        "rate_count": sum(codes.values()),
        **extra,
    }
