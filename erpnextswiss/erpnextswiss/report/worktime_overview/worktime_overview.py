# Copyright (c) 2013, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import date_diff, getdate, add_days
from datetime import date, timedelta
from erpnext.hr.doctype.leave_application.leave_application import get_leave_details
from frappe.utils import cint

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
        {"label": _("Difference in hours"), "fieldname": "difference", "fieldtype": "Float", "width": 150},
        {"label": _("Current holiday balance in days"), "fieldname": "holiday_balance", "fieldtype": "Float", "width": 202}
    ]
    columns = add_activity_type_determination(filters, columns)
    return columns
    
def get_data_of_employee(filters):
    if filters.employee:
        employee = frappe.get_doc("Employee", filters.employee)
    else:
        employee_name = get_employee_name(frappe.session.user)
        employee = frappe.get_doc("Employee", employee_name)
        
    actual = get_actual_time(filters, employee.name)
    target = get_target_time(filters, employee.name)
    diff = actual - target
    data = []
    
    _data = [
        employee.name,
        employee.employee_name,
        target,
        actual,
        diff,
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
        actual = get_actual_time(filters, employee.name)
        target = get_target_time(filters, employee.name)
        diff = actual - target
        
        _data = [
            employee.name,
            employee.employee_name,
            target,
            actual,
            diff,
            get_holiday_balance(employee.name, filters.to_date)
        ]
        
        activity_type_determinations = get_activity_type_determinations(filters, employee.name)
        for activity_type_determination in activity_type_determinations:
            _data.append(activity_type_determination)
            
        data.append(_data)
    
    return data


def get_target_time(filters, employee):
    degrees = get_degrees(employee)
    
    # if more than one degree
    if len(degrees) > 1:
        working_hours = 0
        target_per_day = get_daily_hours(filters)
        degree_list = []
        i = 0
        i_max = len(degrees) - 1
        while i < len(degrees):
            data = {}
            if i != i_max:
                data["start"] = degrees[i].date.strftime("%Y-%m-%d")
                data["end"] = add_days(degrees[i + 1].date.strftime("%Y-%m-%d"), -1)
                data["degree"] = degrees[i].degree
            else:
                data["start"] = degrees[i].date.strftime("%Y-%m-%d")
                data["end"] = filters.to_date
                data["degree"] = degrees[i].degree
            degree_list.append(data)
            i += 1
            
        employee_joining_date = frappe.get_doc("Employee", employee).date_of_joining
        if getdate(employee_joining_date) < getdate(filters.from_date):
            start_date = getdate(filters.from_date)
        else:
            start_date = getdate(employee_joining_date)
            
        end_date = getdate(filters.to_date)
        delta = timedelta(days=1)
        while start_date <= end_date:
            for degree_range in degree_list:
                if getdate(degree_range["start"]) <= start_date <= getdate(degree_range["end"]):
                    working_hours += (((1 - get_off_days(start_date.strftime("%Y-%m-%d"), start_date.strftime("%Y-%m-%d"), filters.company)) * target_per_day) / 100 ) * degree_range["degree"]
            start_date += delta
        return working_hours
        
    # if only one degree or no degrees
    else:
        employee_joining_date = frappe.get_doc("Employee", employee).date_of_joining
        if getdate(employee_joining_date) < getdate(filters.from_date):
            start_date = filters.from_date
        else:
            start_date = employee_joining_date
            
        days = date_diff(filters.to_date, start_date) + 1
        off_days = get_off_days(start_date, filters.to_date, filters.company)
        if len(degrees) > 0:
            target_per_day = (get_daily_hours(filters) / 100) * degrees[0].degree
        else:
            target_per_day = get_daily_hours(filters)
        target_time = (days - off_days) * target_per_day
    return target_time
    
def get_degrees(employee):
    degrees = frappe.db.sql("""SELECT `degree`, `date` FROM `tabEmployment Degree` WHERE `parent` = '{employee}' ORDER BY `date` ASC""".format(employee=employee), as_dict=True)
    return degrees
    
def get_off_days(from_date, to_date, company):
    off_days = 0
    year = getdate(from_date).strftime("%Y")
    
    holiday_lists = frappe.db.sql("""SELECT `year`, `public_holiday_list` FROM `tabPublic Holiday List` WHERE `year` = '{year}' AND `company` = '{company}' LIMIT 1""".format(year=year, company=company), as_dict=True)
    if len(holiday_lists) > 0:
        holiday_list = holiday_lists[0].public_holiday_list
        _holiday_list_entries = frappe.db.sql("""SELECT `holiday_date` FROM `tabHoliday` WHERE `parent` = '{holiday_list}'""".format(holiday_list=holiday_list), as_list=True)
        holiday_list_entries = []
        for entry in _holiday_list_entries:
            holiday_list_entries.append(entry[0])
            
        start_date = getdate(from_date)
        end_date = getdate(to_date)
        delta = timedelta(days=1)
        while start_date <= end_date:
            if start_date in holiday_list_entries:
                off_days += 1
            start_date += delta
            
    return off_days
    
def get_holiday_balance(employee, to_date):
    leave_details = get_leave_details(employee, to_date)
    
    remaining_days = 0
    
    for key in leave_details["leave_allocation"]:
        remaining_days += float(leave_details["leave_allocation"][key]["remaining_leaves"])
    
    return float(remaining_days)
    
def get_actual_time(filters, employee):
    from_date = filters.from_date
    to_date = filters.to_date
    try:
        actual_time = frappe.db.sql("""SELECT SUM(`hours`) FROM `tabTimesheet Detail`
                                        WHERE DATE(`from_time`) >= '{from_date}' AND DATE(`from_time`) <= '{to_date}'
                                        AND `docstatus` = 1 AND `parent` IN (
                                            SELECT `name` FROM `tabTimesheet` WHERE `employee` = '{employee}'
                                        )""".format(from_date=from_date, to_date=to_date, employee=employee), as_list=True)[0][0]
        if not actual_time:
            actual_time = 0
    except:
        actual_time = 0
        
    if cint(filters.get('ignore_py')) == 1:
        return actual_time
    
    # handle carryover and payouts
    employee = frappe.get_doc("Employee", employee)
    if employee.carryover_and_payouts:
        year = getdate(from_date).strftime("%Y")
        for cp in employee.carryover_and_payouts:
            if str(cp.year) == year:
                actual_time += cp.amount
                
    return actual_time

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
    
def get_daily_hours(filters):
    try:
        daily_hours = frappe.db.sql("""SELECT `daily_hours` FROM `tabDaily Hours` WHERE `company` = '{company}' LIMIT 1""".format(company=filters.company), as_list=True)[0][0]
    except:
        # fallback
        daily_hours = 8
    return daily_hours
    
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

def get_employee_overtime(filters):   
    data = get_data_of_employee(filters)
    return round(data[0][4], 3)
