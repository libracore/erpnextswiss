# Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, flt
from erpnextswiss.scripts.worktime_utils import check_holiday_hours

def execute(filters=None):
    columns = get_columns(filters)
    if "HR Manager" in frappe.get_roles(frappe.session.user):
        if filters.employee:
            # only filtered employee
            data = get_data(filters)
        else:
            # all employees
            data = get_data_of_all_employees(filters)
    else:
        # only own employee
        data = get_data(filters)

    return columns, data

def get_columns(filters):
    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 140
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("FTE"),
            "fieldname": "fte",
            "fieldtype": "Percent",
            "width": 80
        },
        {
            "label": _("Recorded Hours"),
            "fieldname": "recorded_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 120
        },
        {
            "label": _("Half Day Hours"),
            "fieldname": "half_day_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 120
        },
        {
            "label": _("Full Day Hours"),
            "fieldname": "full_day_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 120
        },
        {
            "label": _("Deviation"),
            "fieldname": "deviation",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Day Off"),
            "fieldname": "is_day_off",
            "fieldtype": "Check",
            "width": 80
        },
        {
            "label": _("Valid"),
            "fieldname": "is_valid",
            "fieldtype": "Check",
            "width": 70
        }
    ]

    return columns

def get_data(filters):
    if filters.employee:
        employee = frappe.get_doc("Employee", filters.employee)
    else:
        employee_name = get_employee_name(frappe.session.user)
        employee = frappe.get_doc("Employee", employee_name)
    
    check_result = check_holiday_hours(employee.name, filters.company, filters.from_date, filters.to_date)

    rows = []

    for day in check_result.get("days", []):
        deviation = day.get("deviation_hours", {})

        deviation_min = flt(deviation.get("min"))
        deviation_max = flt(deviation.get("max"))

        if deviation_min == deviation_max:
            deviation_text = "{0:.2f} h".format(deviation_min)
        else:
            deviation_text = "{0:.2f}–{1:.2f} h".format(deviation_min, deviation_max)

        rows.append({
            "employee": employee.name,
            "employee_name": employee.employee_name,
            "date": day.get("date"),
            "fte": flt(day.get("fte")) * 100,
            "recorded_hours": flt(day.get("recorded_hours")),
            "half_day_hours": flt(day.get("half_day_hours")),
            "full_day_hours": flt(day.get("full_day_hours")),
            "deviation": deviation_text,
            "is_day_off": 1 if day.get("is_day_off") else 0,
            "is_valid": 1 if day.get("is_valid") else 0
        })

    return rows

def get_data_of_all_employees(filters):
    employees = frappe.db.sql("""
        SELECT `name`, `employee_name` 
        FROM `tabEmployee` 
        WHERE 
            `company` = "{company}"
            AND (`relieving_date` IS NULL OR `relieving_date` >= "{start_date}")
        ;""".format(company=filters.company, start_date=getdate(filters.from_date)), as_dict=True)
    
    master_rows = []

    for employee in employees:
        lookup_filters = frappe._dict()
        lookup_filters.employee = employee.name
        lookup_filters.company = filters.company
        lookup_filters.from_date = filters.from_date
        lookup_filters.to_date = filters.to_date
        employee_rows = get_data(lookup_filters)
        for row in employee_rows:
            master_rows.append(row)
    
    return master_rows

def get_employee_name(user):
    employee = frappe.db.sql("""SELECT `name` FROM `tabEmployee` WHERE `user_id` = '{user}'""".format(user=user), as_dict=True)
    try:
        employee = employee[0].name
    except:
        frappe.throw(_("No Employee found."))
    return employee