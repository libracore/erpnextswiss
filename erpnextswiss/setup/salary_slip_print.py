"""Owned KT salary print format, reapplied on install/migrate without touching payroll."""

from pathlib import Path

import frappe


FORMAT_NAME = "KT Lohnabrechnung"
COMPANY_NAME = "KT Wärmesysteme AG"
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "print_formats" / "kt_salary_slip.html"


def print_format_definition():
    return {
        "doctype": "Print Format",
        "name": FORMAT_NAME,
        "doc_type": "Salary Slip",
        "module": "ERPNextSwiss",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "Jinja",
        "default_print_language": "de",
        "pdf_generator": "wkhtmltopdf",
        "disabled": 0,
        "html": TEMPLATE.read_text(encoding="utf-8"),
        "css": "",
        "format_data": None,
        "print_format_builder": 0,
        "print_format_builder_beta": 0,
        "raw_printing": 0,
        "font": "Arial",
        "font_size": 10,
        "margin_top": 16,
        "margin_bottom": 16,
        "margin_left": 18,
        "margin_right": 18,
        "page_number": "Hide",
    }


def sync_salary_slip_print_format():
    """Scope ownership to KT sites with optional HRMS installed; idempotent upsert."""
    if not frappe.db.exists("DocType", "Salary Slip") or not frappe.db.exists("Company", COMPANY_NAME):
        return
    definition = print_format_definition()
    if frappe.db.exists("Print Format", FORMAT_NAME):
        record = frappe.get_doc("Print Format", FORMAT_NAME)
        if record.doc_type != "Salary Slip":
            frappe.throw(f"Print Format {FORMAT_NAME} belongs to another DocType")
        changes = {key: value for key, value in definition.items() if key not in ("name", "doctype") and record.get(key) != value}
        if changes:
            record.update(changes)
            record.save(ignore_permissions=True)
    else:
        frappe.get_doc(definition).insert(ignore_permissions=True)

    if frappe.get_meta("Salary Slip").default_print_format != FORMAT_NAME:
        from frappe.custom.doctype.property_setter.property_setter import make_property_setter

        make_property_setter("Salary Slip", None, "default_print_format", FORMAT_NAME, "Data", for_doctype=True)
        frappe.clear_cache(doctype="Salary Slip")
