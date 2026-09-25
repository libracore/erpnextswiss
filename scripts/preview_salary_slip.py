"""Render the candidate template through native Frappe/wkhtmltopdf, read-only.

Run using the bench Python. Never inserts a Print Format, changes payroll, sends
mail or commits. The candidate is selected only in this isolated Python process.
"""

import argparse
import importlib.util
from pathlib import Path
from unittest.mock import patch

import frappe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--sites-path", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--slip", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stress", action="store_true", help="Synthetic long/multipage document, never saved")
    args = parser.parse_args()
    frappe.init(site=args.site, sites_path=args.sites_path)
    try:
        frappe.connect()
        frappe.set_user(args.user)
        frappe.local.lang = "de"
        frappe.db.rollback()
        frappe.db.sql("START TRANSACTION READ ONLY")
        source = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("candidate_salary_print", source / "erpnextswiss/setup/salary_slip_print.py")
        candidate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(candidate)
        print_format = frappe.get_doc(candidate.print_format_definition())
        from frappe.www import printview

        frappe.form_dict.settings = frappe.as_json({"allow_print_for_draft": 1, "allow_print_for_cancelled": 1})
        doc = None
        if args.stress:
            doc = frappe.get_doc("Salary Slip", args.slip)
            doc.name = "SYNTHETISCH-KEINE-ECHTE-ABRECHNUNG"
            doc.employee = "TEST-PERSON"
            doc.employee_name = "Layout-Prüfung mit einem besonders langen Mitarbeiternamen"
            doc.docstatus = 2
            doc.bank_name = None
            doc.bank_account_no = None
            doc.set("deductions", [])
            for number in range(36):
                doc.append("deductions", {"salary_component": f"Testabzug {number + 1:02d} mit einer besonders langen Bezeichnung für den kontrollierten Seitenumbruch", "amount": 10})
            doc.total_deduction = 360
            doc.net_pay = doc.gross_pay - doc.total_deduction
            doc.rounded_total = doc.net_pay
        with patch.object(printview, "get_print_format_doc", return_value=print_format), patch.object(printview, "make_access_log"):
            pdf = frappe.get_print("Salary Slip", args.slip, candidate.FORMAT_NAME, doc=doc, as_pdf=True, pdf_generator="wkhtmltopdf")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(pdf)
        print(f"READ_ONLY_PREVIEW_OK bytes={len(pdf)}")
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
