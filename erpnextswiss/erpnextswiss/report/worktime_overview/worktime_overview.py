# Copyright (c) 2013, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.data import getdate
from erpnext.hr.doctype.leave_application.leave_application import get_leave_details
from erpnextswiss.scripts.worktime_utils import get_worktime_overview

def execute(filters=None):
    if "HR Manager" in frappe.get_roles(frappe.session.user):
        if filters.employee:
            # only filtered employee
            columns, data = get_columns(filters), get_data_of_employee(filters)
        else:
            # all employees
            columns, data = get_columns(filters), get_data_of_all_employees(filters)
    else:
        # only own employee
        columns, data = get_columns(filters), get_data_of_employee(filters)
    
    return columns, data

def get_employee_name(user):
    employee = frappe.db.sql("""SELECT `name` FROM `tabEmployee` WHERE `user_id` = '{user}'""".format(user=user), as_dict=True)
    try:
        employee = employee[0].name
    except:
        frappe.throw(_("No Employee found."))
    return employee

def get_columns(filters):
    columns = [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": _("Target time in hours"), "fieldname": "target_time", "fieldtype": "Float", "width": 150},
        {"label": _("Actual time in hours"), "fieldname": "actual_time", "fieldtype": "Float", "width": 150},
        {"label": _("Opening Balance"), "fieldname": "opening_balance", "fieldtype": "Float", "width": 150},
        {"label": _("Difference in hours"), "fieldname": "difference", "fieldtype": "Float", "width": 150},
        {"label": _("Closing Balance"), "fieldname": "closing_balance", "fieldtype": "Float", "width": 150},
        {"label": _("Warnungen"), "fieldname": "warnings", "fieldtype": "Data", "width": 150},
        {"label": _("Current holiday balance in days"), "fieldname": "holiday_balance", "fieldtype": "Float", "width": 202}
    ]

    columns = add_activity_type_determination(filters, columns)

    return columns
    
def get_data_of_employee(filters, ignore_carryover=False):
    if filters.employee:
        employee = frappe.get_doc("Employee", filters.employee)
    else:
        employee_name = get_employee_name(frappe.session.user)
        employee = frappe.get_doc("Employee", employee_name)
    
    data = []
    worktime_overview = get_worktime_overview(employee.name, filters.company, filters.from_date, filters.to_date)
    actual = flt(worktime_overview.get('actual_time', 0)) + flt(worktime_overview.get('holidays_in_hours', 0), 2)
    target = flt(worktime_overview.get('target_time'), 2)
    opening_balance = flt(worktime_overview.get('opening_balance'), 2)
    diff = flt(worktime_overview.get('overtime'), 2)
    closing_balance = flt(worktime_overview.get('closing_balance'), 2)
    
    holiday_hours_check = worktime_overview.get('holiday_hours_check')
    warning = 'Keine'

    if holiday_hours_check:
        summary = holiday_hours_check.get("summary", {})

        invalid_days = summary.get("number_of_invalid_days", 0)
        deviation = summary.get("deviation_hours", {})

        if invalid_days:
            deviation_min = flt(deviation.get("min"))
            deviation_max = flt(deviation.get("max"))

            if deviation_min == deviation_max:
                warning = _("{0} fehlerhafte Ferientage; Abweichung: {1} Std.").format(invalid_days, deviation_min)
            else:
                warning = _("{0} fehlerhafte Ferientage; Abweichung: {1} bis {2} Std.").format(invalid_days, deviation_min, deviation_max)
    
    _data = [
        employee.name,
        employee.employee_name,
        target,
        actual,
        opening_balance,
        diff,
        closing_balance,
        warning,
        get_holiday_balance(employee.name, filters.to_date)
    ]
    
    activity_type_determinations = get_activity_type_determinations(filters, employee.name)

    for activity_type_determination in activity_type_determinations:
        _data.append(activity_type_determination)
        
    data.append(_data)
    
    return data
    
def get_data_of_all_employees(filters):
    employees = frappe.db.sql("""
        SELECT `name`, `employee_name` 
        FROM `tabEmployee` 
        WHERE 
            `company` = "{company}"
            AND (`relieving_date` IS NULL OR `relieving_date` >= "{start_date}")
        ;""".format(company=filters.company, start_date=getdate(filters.from_date)), as_dict=True)
    data = []
    
    for _employee in employees:
        employee = frappe.get_doc("Employee", _employee.name)
        worktime_overview = get_worktime_overview(employee.name, filters.company, filters.from_date, filters.to_date)
        actual = flt(worktime_overview.get('actual_time', 0)) + flt(worktime_overview.get('holidays_in_hours', 0), 2)
        target = flt(worktime_overview.get('target_time'), 2)
        opening_balance = flt(worktime_overview.get('opening_balance'), 2)
        diff = flt(worktime_overview.get('overtime'), 2)
        closing_balance = flt(worktime_overview.get('closing_balance'), 2)

        holiday_hours_check = worktime_overview.get('holiday_hours_check')
        warning = 'Keine'
        
        if holiday_hours_check:
            summary = holiday_hours_check.get("summary", {})

            invalid_days = summary.get("number_of_invalid_days", 0)
            deviation = summary.get("deviation_hours", {})

            if invalid_days:
                deviation_min = flt(deviation.get("min"))
                deviation_max = flt(deviation.get("max"))

                if deviation_min == deviation_max:
                    warning = _("{0} fehlerhafte Ferientage; Abweichung: {1} Std.").format(invalid_days, deviation_min)
                else:
                    warning = _("{0} fehlerhafte Ferientage; Abweichung: {1} bis {2} Std.").format(invalid_days, deviation_min, deviation_max)
        
        _data = [
            employee.name,
            employee.employee_name,
            target,
            actual,
            opening_balance,
            diff,
            closing_balance,
            warning,
            get_holiday_balance(employee.name, filters.to_date)
        ]
        
        activity_type_determinations = get_activity_type_determinations(filters, employee.name)
        
        for activity_type_determination in activity_type_determinations:
            _data.append(activity_type_determination)
            
        data.append(_data)
    
    return data
    
def get_holiday_balance(employee, to_date):
    leave_details = get_leave_details(employee, to_date)
    
    remaining_days = 0
    
    for key in leave_details["leave_allocation"]:
        remaining_days += float(leave_details["leave_allocation"][key]["remaining_leaves"])
    
    return float(remaining_days)

def add_activity_type_determination(filters, columns):
    additions = frappe.db.sql("""SELECT `company`, `activity_type`, `column_label` FROM `tabActivity Type Determination` WHERE `company` = '{company}' ORDER BY `idx` ASC""".format(company=filters.company), as_dict=True)
    loop = 1
    for addition in additions:
        new_column = {"label": _(addition.column_label), "fieldname": "annex_" + str(loop), "fieldtype": "Float", "width": 50}
        columns.append(new_column)
        loop += 1
    return columns
    
def get_activity_type_determinations(filters, employee):
    from_date = filters.from_date
    to_date = filters.to_date
    times = []
    additions = frappe.db.sql("""SELECT `company`, `activity_type`, `column_label` FROM `tabActivity Type Determination` WHERE `company` = '{company}' ORDER BY `idx` ASC""".format(company=filters.company), as_dict=True)
    for addition in additions:
        try:
            actual_time = frappe.db.sql("""SELECT SUM(`hours`) FROM `tabTimesheet Detail`
                                            WHERE DATE(`from_time`) >= '{from_date}' AND DATE(`from_time`) <= '{to_date}'
                                            AND `docstatus` = 1 AND `activity_type` = '{activity_type}' AND `parent` IN (
                                                SELECT `name` FROM `tabTimesheet` WHERE `employee` = '{employee}'
                                            )""".format(from_date=from_date, to_date=to_date, employee=employee, activity_type=addition.activity_type), as_list=True)[0][0]
            if not actual_time:
                actual_time = 0
        except:
            actual_time = 0
        times.append(actual_time)
        
    return times
    
@frappe.whitelist()
def get_company():
    user = frappe.session.user
    employee = frappe.db.sql("""SELECT `name` FROM `tabEmployee` WHERE `user_id` = '{user}'""".format(user=user), as_dict=True)
    try:
        employee_name = employee[0].name
        employee = frappe.get_doc("Employee", employee_name)
        company = employee.company
    except:
        # fallback
        company = frappe.get_single("Global Defaults").default_company
    return company
    
@frappe.whitelist()
def get_employee_overview_html(employee, company, from_date, to_date):
    filters = frappe._dict()
    filters.employee = employee
    filters.from_date = from_date
    filters.to_date = to_date
    filters.company = company
    
    data = get_data_of_employee(filters)
    
    if len(data) > 0:
        data = data[0]
        html = '<table style="width: 100%;"><thead><tr><th>'
        html += '</th><th>'.join([_("Target time in hours"), _("Actual time in hours"), _("Difference in hours"), _("Current holiday balance in days")])
        html += '</th></tr></thead><tbody><tr><td>'
        html += '</td><td>'.join([str(round(data[2], 3)), str(round(data[3], 3)), str(round(data[4], 3)), str(data[5])])
        html += '</td><td></tr></tbody></table>'
    else:
        html = _('<div>No data found</div>')
    
    return html
