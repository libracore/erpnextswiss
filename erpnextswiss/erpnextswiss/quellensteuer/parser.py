import hashlib
import io
import re
import zipfile
from datetime import date

FILE_PATTERN = re.compile(r"(?:^|/)tar(\d{2})([a-z]{2})\.txt$", re.IGNORECASE)
DATA_RECORDS = ("06", "11", "12", "13")
EXCLUDED_GROUPS = "RSTUV"


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


def parse(text):
    """Parse one ESTV tariff file (record format D_DVS 0005) into a dict."""
    lines = [line.rstrip("\r\n") for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].startswith("00") or not lines[-1].startswith("99"):
        raise TariffFileError("Header or trailer record missing")
    canton, trailer = lines[0][2:4], lines[-1]
    if trailer[17:19] != canton:
        raise TariffFileError(f"Trailer canton {trailer[17:19]} does not match {canton}")
    if int(trailer[19:27]) != len(lines):
        raise TariffFileError(f"{canton}: trailer announces {int(trailer[19:27])} records, found {len(lines)}")
    rows, data_lines, extra = [], [], {"commission": {}, "median_value": 0}
    for number, line in enumerate(lines[1:-1], start=2):
        record_type, code = line[0:2], line[6:16].strip()
        if record_type not in DATA_RECORDS or line[4:6] != canton:
            raise TariffFileError(f"{canton}: invalid record in line {number}")
        if line[2:4] != "01":
            raise TariffFileError(f"{canton}: transaction type {line[2:4]} in line {number} is not supported")
        data_lines.append(line)
        if record_type == "12":
            extra["commission"][code] = to_amount(line[54:59])
        elif record_type == "13":
            extra["median_value"] = to_amount(line[45:54])
        elif code[:1] not in EXCLUDED_GROUPS or record_type == "11":
            rows.append({
                "record_type": record_type,
                "code": code,
                "valid_from": to_date(line[16:24]),
                "income_from": to_amount(line[24:33]),
                "step": to_amount(line[33:42]),
                "children": int(line[43:45].strip() or 0),
                "min_tax": to_amount(line[45:54]),
                "rate": to_amount(line[54:59]),
            })
    if not rows:
        raise TariffFileError(f"{canton}: no tariff records")
    return {
        "canton": canton,
        "creation_date": to_date(lines[0][19:27]),
        "header_text": " ".join(lines[0][27:107].split()),
        "record_count": len(lines),
        "valid_from": min(row["valid_from"] for row in rows),
        "content_hash": hashlib.sha256("\n".join(sorted(data_lines)).encode()).hexdigest(),
        "rows": rows,
        **extra,
    }
