from zipfile import BadZipFile

import frappe
from frappe import _
from frappe.database.sequence import get_next_val, set_next_val
from frappe.utils import now
from frappe.utils.background_jobs import is_job_enqueued
from frappe.utils.synchronization import filelock

from erpnextswiss.erpnextswiss.quellensteuer.parser import (
    TariffFileError, code_rows, iter_tariff_files, parse)

RATE_FIELDS = ["tariff", "record_type", "code", "valid_from", "income_from", "step", "children", "min_tax", "rate"]
IMPORT_JOB = "qst_tariff_import"


@frappe.whitelist()
def start_import(name):
    """Queue the import of an uploaded ESTV tariff file."""
    doc = frappe.get_doc("QST Tariff Import", name)
    doc.check_permission("write")
    if is_job_enqueued(IMPORT_JOB):
        frappe.throw(_("Another tariff import is queued or running. Please start this import when it has finished."))
    doc.db_set("status", "Queued")
    frappe.enqueue(import_tariffs, queue="long", timeout=7200, job_id=IMPORT_JOB, deduplicate=True, name=name, enqueue_after_commit=True)


def tariff_name(data):
    return "QST-{0}-{1}-{2:%Y%m%d}".format(data["canton"], data["valid_from"].year, data["creation_date"])


def import_tariffs(name):
    """Import all tariff files of a zip; nothing is stored if any file is invalid or conflicts."""
    doc = frappe.get_doc("QST Tariff Import", name)
    log = []
    try:
        with filelock(IMPORT_JOB, timeout=5):
            run_import(doc, log)
        status = "Completed"
    except Exception as err:
        frappe.db.rollback()
        log.append(str(err))
        status = "Failed"
    doc.db_set({"status": status, "log": "\n".join(log)})
    frappe.db.commit()


def run_import(doc, log):
    """Store the tariff revisions of an ESTV file; rate rows stay in the file until used."""
    content = frappe.get_doc("File", {"file_url": doc.file}).get_content()
    plan, conflicts = [], []
    for canton, text in iter_tariff_files(content):
        data = parse(text)
        existing = frappe.db.get_value("QST Tariff", tariff_name(data), "content_hash")
        latest = frappe.db.get_value("QST Tariff", {"canton": data["canton"], "year": data["valid_from"].year},
                                     "content_hash", order_by="creation_date desc")
        if existing and existing != data["content_hash"]:
            conflicts.append(_("{0}: revision already imported with different data").format(tariff_name(data)))
        elif existing or latest == data["content_hash"]:
            log.append(_("{0}: already imported, skipped").format(tariff_name(data)))
        else:
            plan.append(data)
    if conflicts:
        raise TariffFileError("\n".join(conflicts))
    if not plan and not log:
        raise TariffFileError(_("No tariff files found"))
    for data in plan:
        store(data, doc.name)
        frappe.db.commit()
        log.append(_("{0}: {1} tariff codes, {2} rates available").format(tariff_name(data), len(data["codes"]), data["rate_count"]))


def store(data, import_name):
    """Insert a tariff revision with its available codes; rates are loaded per code on first use."""
    return frappe.get_doc({
        "doctype": "QST Tariff",
        "canton": data["canton"],
        "year": data["valid_from"].year,
        "valid_from": data["valid_from"],
        "creation_date": data["creation_date"],
        "calculation_model": frappe.db.get_value("QST Canton", data["canton"], "calculation_model") or "Monthly",
        "header_text": data["header_text"],
        "record_count": data["record_count"],
        "rate_count": data["rate_count"],
        "content_hash": data["content_hash"],
        "median_value": data["median_value"],
        "commission_pel": data["commission"].get("PEL"),
        "commission_ppa": data["commission"].get("PPA"),
        "commission_psp": data["commission"].get("PSP"),
        "first_imported_on": now(),
        "tariff_import": import_name,
        "codes": [{"code": code, "rate_count": count} for code, count in sorted(data["codes"].items())],
    }).insert(ignore_permissions=True)


def source_text(tariff):
    """ESTV file content of a tariff revision: its own import first, then any other import holding the same revision."""
    doc = frappe.get_cached_doc("QST Tariff", tariff)
    others = frappe.get_all("QST Tariff Import", filters={"name": ("!=", doc.tariff_import or "")}, order_by="creation desc", pluck="name")
    for name in ([doc.tariff_import] if doc.tariff_import else []) + others:
        file_url = frappe.db.get_value("QST Tariff Import", name, "file")
        source = frappe.db.exists("File", {"file_url": file_url}) if file_url else None
        if not source:
            continue
        try:
            for canton, text in iter_tariff_files(frappe.get_doc("File", source).get_content(), {doc.canton}):
                if parse(text)["content_hash"] == doc.content_hash:
                    return text
        except (TariffFileError, BadZipFile, OSError):
            continue
    frappe.throw(_("The ESTV file of tariff {0} is no longer available, please import it again").format(tariff))


def insert_rates(tariff, rows):
    """Store rate rows with reserved autoincrement names."""
    if not rows:
        return
    timestamp, user, first = now(), frappe.session.user, get_next_val("QST Tariff Rate")
    frappe.db.bulk_insert(
        "QST Tariff Rate",
        ["name"] + RATE_FIELDS + ["creation", "modified", "owner", "modified_by"],
        ([first + i, tariff] + [row[field] for field in RATE_FIELDS[1:]] + [timestamp, timestamp, user, user]
         for i, row in enumerate(rows)),
    )
    set_next_val("QST Tariff Rate", first + len(rows) - 1, is_val_used=True)


def ensure_code(tariff, code):
    """Load the rates of one tariff code on first use; False if the code is not in the ESTV file."""
    row = frappe.db.get_value("QST Tariff Code", {"parent": tariff, "code": code}, ["name", "loaded"], as_dict=True)
    if not row:
        return False
    if row.loaded:
        return True
    with filelock("qst_rates_{0}_{1}".format(tariff, code), timeout=300):
        if frappe.db.get_value("QST Tariff Code", row.name, "loaded"):
            return True
        rows = list(code_rows(source_text(tariff), code))
        frappe.db.delete("QST Tariff Rate", {"tariff": tariff, "code": code})
        insert_rates(tariff, rows)
        frappe.db.set_value("QST Tariff Code", row.name, "loaded", 1, update_modified=False)
    return True


def cache():
    if not hasattr(frappe.local, "qst_cache"):
        frappe.local.qst_cache = {}
    return frappe.local.qst_cache


def get_tariff(canton, day):
    """Latest imported tariff revision of a canton valid on a day."""
    key = ("tariff", canton, day)
    if key not in cache():
        tariffs = frappe.db.sql("""
            SELECT `name`, `calculation_model`, `canton`, `median_value`
            FROM `tabQST Tariff`
            WHERE `canton` = %s AND `year` = %s AND `valid_from` <= %s
            ORDER BY `creation_date` DESC, `first_imported_on` DESC
            LIMIT 1""", (canton, day.year, day), as_dict=True)
        cache()[key] = tariffs[0] if tariffs else None
    return cache()[key]


def variants(code):
    """The code itself and its other church tax variant."""
    return (code, code[:-1] + ("N" if code.endswith("Y") else "Y"))


def get_bracket(tariff, code, income):
    """Tariff bracket for a code and monthly rate-determining income; falls back to the other church tax variant."""
    key = ("bracket", tariff, code, round(income, 2))
    if key not in cache():
        cache()[key] = None
        for candidate in variants(code):
            if not ensure_code(tariff, candidate):
                continue
            brackets = frappe.db.sql("""
                SELECT `code`, `income_from`, `step`, `min_tax`, `rate`
                FROM `tabQST Tariff Rate`
                WHERE `tariff` = %s AND `code` = %s
                ORDER BY `income_from` <= %s DESC, IF(`income_from` <= %s, -`income_from`, `income_from`)
                LIMIT 1""", (tariff, candidate, income, income), as_dict=True)
            if brackets:
                cache()[key] = brackets[0]
                break
    return cache()[key]


def prefetch(tariff, code):
    """Load the rates a code needs, using the other church tax variant when it has none of its own."""
    return any(ensure_code(tariff, candidate) for candidate in variants(code))


def has_code(tariff, code):
    """True if the ESTV file of a tariff contains the code or its other church tax variant."""
    return bool(frappe.db.exists("QST Tariff Code", {"parent": tariff, "code": ("in", variants(code))}))
