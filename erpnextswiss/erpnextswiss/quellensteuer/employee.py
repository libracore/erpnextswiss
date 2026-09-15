import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from erpnextswiss.erpnextswiss.quellensteuer import is_enabled
from erpnextswiss.erpnextswiss.quellensteuer.calculation import tariff_code
from erpnextswiss.erpnextswiss.quellensteuer.payroll import DEGREE_MODES, own_degree
from erpnextswiss.erpnextswiss.quellensteuer.tariff import get_tariff, has_code


def validate_employee(doc, method=None):
    """Validate Quellensteuer records and derive tariff codes."""
    if not doc.get("qst_records") or not is_enabled():
        return
    seen = set()
    for row in doc.qst_records:
        valid_from = getdate(row.valid_from)
        if valid_from.day != 1:
            frappe.throw(_("Quellensteuer row {0}: valid from must be the first day of a month").format(row.idx))
        if valid_from in seen:
            frappe.throw(_("Quellensteuer row {0}: duplicate valid from date").format(row.idx))
        seen.add(valid_from)
        if not row.liable:
            row.tariff_code = None
            continue
        if not row.canton or not row.tariff_group:
            frappe.throw(_("Quellensteuer row {0}: canton and tariff group are required").format(row.idx))
        row.tariff_code = tariff_code(row.tariff_group, row.children, row.church_tax)
        if row.other_employment in DEGREE_MODES:
            degree = own_degree(doc, valid_from)
            if not degree:
                frappe.throw(_("Quellensteuer row {0}: {1} requires an employment degree (Employment Degrees) in {2:%m.%Y}").format(
                    row.idx, _(row.other_employment), valid_from))
            if row.other_employment == "Total Degree" and flt(row.total_degree) < degree:
                frappe.throw(_("Quellensteuer row {0}: total employment degree must be at least {1}%").format(row.idx, degree))
        if not frappe.db.get_value("QST Canton", row.canton, "import_tariffs"):
            frappe.db.set_value("QST Canton", row.canton, "import_tariffs", 1)
        tariff = get_tariff(row.canton, max(valid_from, getdate(today()).replace(month=1, day=1)))
        if tariff and not has_code(tariff.name, row.tariff_code):
            frappe.msgprint(_("Tariff code {0} does not exist in {1}").format(row.tariff_code, tariff.name), alert=True)
