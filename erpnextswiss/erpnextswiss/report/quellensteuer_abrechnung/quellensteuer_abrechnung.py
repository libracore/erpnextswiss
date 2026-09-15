# Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from erpnextswiss.erpnextswiss.quellensteuer.payroll import get_record


def execute(filters=None):
    filters = frappe._dict(filters or {})
    data = get_data(filters)
    return get_columns(), data, None, None, get_summary(data, filters)


def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": _("Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": _("AHV Number"), "fieldname": "social_security_number", "fieldtype": "Data", "width": 120},
        {"label": _("Date of Birth"), "fieldname": "date_of_birth", "fieldtype": "Date", "width": 95},
        {"label": _("BFS Number"), "fieldname": "bfsnr", "fieldtype": "Data", "width": 80},
        {"label": _("Entry"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 95},
        {"label": _("Exit"), "fieldname": "relieving_date", "fieldtype": "Date", "width": 95},
        {"label": _("Canton"), "fieldname": "canton", "fieldtype": "Data", "width": 60},
        {"label": _("Period"), "fieldname": "period", "fieldtype": "Date", "width": 95},
        {"label": _("Type"), "fieldname": "entry_type", "fieldtype": "Data", "width": 90},
        {"label": _("Tariff Code"), "fieldname": "tariff_code", "fieldtype": "Data", "width": 80},
        {"label": _("Taxable Income"), "fieldname": "taxable_income", "fieldtype": "Currency", "width": 120},
        {"label": _("Rate-determining Income"), "fieldname": "rate_determining_income", "fieldtype": "Currency", "width": 120},
        {"label": _("Rate %"), "fieldname": "rate", "fieldtype": "Float", "precision": 2, "width": 70},
        {"label": _("Tax"), "fieldname": "tax", "fieldtype": "Currency", "width": 110},
        {"label": _("Salary Slip"), "fieldname": "salary_slip", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
    ]


def get_data(filters):
    conditions = ["`slip`.`docstatus` = 1", "`detail`.`parenttype` = 'Salary Slip'"]
    for key, condition in (("company", "`slip`.`company` = %(company)s"), ("canton", "`detail`.`canton` = %(canton)s"),
                           ("from_date", "`slip`.`start_date` >= %(from_date)s"), ("to_date", "`slip`.`start_date` <= %(to_date)s")):
        if filters.get(key):
            conditions.append(condition)
    rows = frappe.db.sql("""
        SELECT `slip`.`employee`, `slip`.`employee_name`, `slip`.`name` AS `salary_slip`, `employee`.`social_security_number`,
            `employee`.`date_of_birth`, `employee`.`date_of_joining`, `employee`.`relieving_date`, `detail`.`canton`,
            `detail`.`period`, `detail`.`entry_type`, `detail`.`tariff_code`, `detail`.`taxable_income`,
            `detail`.`rate_determining_income`, `detail`.`rate`, `detail`.`tax`, `detail`.`qst_tariff`
        FROM `tabQST Slip Detail` AS `detail`
        JOIN `tabSalary Slip` AS `slip` ON `slip`.`name` = `detail`.`parent`
        JOIN `tabEmployee` AS `employee` ON `employee`.`name` = `slip`.`employee`
        WHERE {0}
        ORDER BY `detail`.`canton`, `slip`.`employee_name`, `detail`.`period`""".format(" AND ".join(conditions)), filters, as_dict=True)
    employees = {}
    for row in rows:
        employee = employees.setdefault(row.employee, frappe.get_doc("Employee", row.employee))
        record = get_record(employee, getdate(row.period))
        row.bfsnr = frappe.get_cached_value("Municipality", record.municipality, "bfsnr") if record and record.municipality else None
    return rows


def get_summary(data, filters):
    total = flt(sum(flt(row.tax) for row in data), 2)
    code = "PEL"
    if filters.get("company") and filters.get("canton"):
        code = frappe.db.get_value("QST Canton Account", {"parent": "QST Settings", "company": filters.company, "canton": filters.canton},
                                   "commission_code") or code
    commission = sum(flt(row.tax) * flt(frappe.get_cached_value("QST Tariff", row.qst_tariff, "commission_" + code.lower())) / 100
                     for row in data if row.qst_tariff)
    return [
        {"label": _("Total Tax"), "value": total, "datatype": "Currency"},
        {"label": _("Commission"), "value": flt(commission, 2), "datatype": "Currency"},
        {"label": _("Net Payable"), "value": flt(total - commission, 2), "datatype": "Currency", "indicator": "Blue"},
    ]
