"""Targeted, backed-up print-format data migration from a reviewed Git archive.

No application code is installed by this command. Its self-contained Jinja data
works in the current container; the same source's after_migrate hook maintains it
in subsequent images. No salary recalculation, submission or email is performed.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import frappe


def digest(rows):
    payload = json.dumps(rows, sort_keys=True, default=str).encode()
    return {"count": len(rows), "sha256": hashlib.sha256(payload).hexdigest()}


def financial_snapshot():
    tables = ("Salary Slip", "Salary Detail", "Salary Structure", "Salary Structure Assignment", "Additional Salary", "Payroll Entry")
    result = {doctype: digest(frappe.get_all(doctype, fields=["*"], order_by="name")) for doctype in tables}
    journals = frappe.get_all("Salary Slip", filters={"journal_entry": ["is", "set"]}, pluck="journal_entry")
    for doctype, filters in (("Journal Entry", {"name": ["in", journals]}), ("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": ["in", journals]})):
        result[doctype] = digest(frappe.get_all(doctype, filters=filters, fields=["*"], order_by="name")) if journals else digest([])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--sites-path", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--template-sha256", required=True)
    parser.add_argument("--sample-slip", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    template = source / "erpnextswiss/templates/print_formats/kt_salary_slip.html"
    assert hashlib.sha256(template.read_bytes()).hexdigest() == args.template_sha256, "Candidate template mismatch"
    spec = importlib.util.spec_from_file_location("reviewed_salary_print", source / "erpnextswiss/setup/salary_slip_print.py")
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    frappe.init(site=args.site, sites_path=args.sites_path)
    try:
        frappe.connect()
        frappe.set_user(args.user)
        if "System Manager" not in frappe.get_roles():
            raise PermissionError("System Manager is required for this metadata migration")
        frappe.local.lang = "de"
        assert frappe.db.exists("Company", candidate.COMPANY_NAME)
        old_format = frappe.get_doc("Print Format", candidate.FORMAT_NAME).as_dict() if frappe.db.exists("Print Format", candidate.FORMAT_NAME) else None
        setters = frappe.get_all("Property Setter", filters={"doc_type": "Salary Slip", "property": "default_print_format"}, fields=["*"])
        before = financial_snapshot()
        backup = Path(args.backup)
        backup.parent.mkdir(parents=True, exist_ok=True)
        with backup.open("x", encoding="utf-8") as stream:
            json.dump({"print_format": old_format, "default_property_setters": setters, "financial_snapshot": before}, stream, ensure_ascii=False, default=str, indent=2)
        os.chmod(backup, 0o600)
        candidate.sync_salary_slip_print_format()
        first = frappe.db.get_value("Print Format", candidate.FORMAT_NAME, "modified")
        candidate.sync_salary_slip_print_format()
        assert first == frappe.db.get_value("Print Format", candidate.FORMAT_NAME, "modified"), "Repeat sync rewrote template"
        assert frappe.get_meta("Salary Slip").default_print_format == candidate.FORMAT_NAME
        # Omit format: exercise actual default resolution, including the legacy letterhead.
        pdf = frappe.get_print("Salary Slip", args.sample_slip, as_pdf=True, pdf_generator="wkhtmltopdf")
        assert before == financial_snapshot(), "Financial record drift; metadata migration rolled back"
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(pdf)
        os.chmod(output, 0o600)
        frappe.db.commit()
        print(json.dumps({"status": "APPLIED", "default": candidate.FORMAT_NAME, "repeat_sync": "NOOP", "financial_records": "UNCHANGED", "template_sha256": args.template_sha256, "pdf_bytes": len(pdf)}))
    finally:
        frappe.db.rollback()
        frappe.clear_cache(doctype="Salary Slip")
        frappe.destroy()


if __name__ == "__main__":
    main()
