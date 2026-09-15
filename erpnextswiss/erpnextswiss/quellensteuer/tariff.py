import frappe
from frappe import _
from frappe.database.sequence import get_next_val, set_next_val
from frappe.utils import now
from frappe.utils.background_jobs import is_job_enqueued
from frappe.utils.synchronization import filelock

from erpnextswiss.erpnextswiss.quellensteuer.parser import TariffFileError, iter_tariff_files, parse

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
    cantons = frappe.get_all("QST Canton", filters={"import_tariffs": 1}, pluck="name")
    content = frappe.get_doc("File", {"file_url": doc.file}).get_content()
    plan, conflicts = [], []
    for canton, text in iter_tariff_files(content, cantons):
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
        raise TariffFileError(_("No tariff files found for cantons marked for import: {0}").format(", ".join(cantons)) if cantons
                              else _("No tariff files found"))
    for data in plan:
        store(data, doc.name)
        frappe.db.commit()
        log.append(_("{0}: imported {1} rates").format(tariff_name(data), len(data["rows"])))


def store(data, import_name):
    """Insert a parsed tariff revision and its rates."""
    tariff = frappe.get_doc({
        "doctype": "QST Tariff",
        "canton": data["canton"],
        "year": data["valid_from"].year,
        "valid_from": data["valid_from"],
        "creation_date": data["creation_date"],
        "calculation_model": frappe.db.get_value("QST Canton", data["canton"], "calculation_model") or "Monthly",
        "header_text": data["header_text"],
        "record_count": data["record_count"],
        "rate_count": len(data["rows"]),
        "content_hash": data["content_hash"],
        "median_value": data["median_value"],
        "commission_pel": data["commission"].get("PEL"),
        "commission_ppa": data["commission"].get("PPA"),
        "commission_psp": data["commission"].get("PSP"),
        "first_imported_on": now(),
        "tariff_import": import_name,
    }).insert(ignore_permissions=True)
    timestamp, user, first = now(), frappe.session.user, get_next_val("QST Tariff Rate")
    frappe.db.bulk_insert(
        "QST Tariff Rate",
        ["name"] + RATE_FIELDS + ["creation", "modified", "owner", "modified_by"],
        ([first + i, tariff.name] + [row[field] for field in RATE_FIELDS[1:]] + [timestamp, timestamp, user, user]
         for i, row in enumerate(data["rows"])),
    )
    set_next_val("QST Tariff Rate", first + len(data["rows"]) - 1, is_val_used=True)


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


def get_bracket(tariff, code, income):
    """Tariff bracket for a code and monthly rate-determining income; falls back to the other church tax variant."""
    key = ("bracket", tariff, code, round(income, 2))
    if key not in cache():
        cache()[key] = None
        for candidate in (code, code[:-1] + ("N" if code.endswith("Y") else "Y")):
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


def has_code(tariff, code):
    return bool(get_bracket(tariff, code, 0))
