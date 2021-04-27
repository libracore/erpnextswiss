# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe.utils.data import date_diff, getdate, add_days
from datetime import date, timedelta
from erpnext.hr.doctype.leave_application.leave_application import get_leave_details

@frappe.whitelist()
def get_data(from_date, to_date, view_type):
    if view_type == 'single':
        data = {}
        data["data"] = {}
        data["data"]["target"] = get_target_time(from_date, to_date, frappe.session.user)
        data["data"]["actual"] = get_actual_time(from_date, to_date, frappe.session.user)
        data["data"]["holiday_balance"] = get_holiday_balance(frappe.session.user, to_date)
        data["view_type"] = 'single'
        return data
        
    if view_type == 'all':
        dataset = []
        employees = frappe.db.sql("""SELECT `name`, `user_id` FROM `tabEmployee` WHERE `user_id` IS NOT NULL""", as_dict=True)
        for employee in employees:
            data = {}
            data["employee"] = employee.name
            data["target"] = get_target_time(from_date, to_date, employee.user_id)
            data["actual"] = get_actual_time(from_date, to_date, employee.user_id)
            data["holiday_balance"] = get_holiday_balance(employee.user_id, to_date)
            dataset.append(data)
            
        return {
            'dataset': dataset,
            'view_type': 'all'
        }
    
def get_target_time(from_date, to_date, user):
    degrees = get_degrees(user)
    
    # if more than one degree
    if len(degrees) > 1:
        working_hours = 0
        target_per_day = frappe.db.get_single_value('Worktime Settings', 'daily_hours')
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
                data["end"] = to_date
                data["degree"] = degrees[i].degree
            degree_list.append(data)
            i += 1
            
        start_date = getdate(from_date)
        end_date = getdate(to_date)
        delta = timedelta(days=1)
        while start_date <= end_date:
            for degree_range in degree_list:
                if getdate(degree_range["start"]) <= start_date <= getdate(degree_range["end"]):
                    working_hours += (((1 - get_off_days(start_date.strftime("%Y-%m-%d"), start_date.strftime("%Y-%m-%d"))) * target_per_day) / 100 ) * degree_range["degree"]
            start_date += delta
        return working_hours
        
    # if only one degree
    else:
        days = date_diff(to_date, from_date) + 1
        off_days = get_off_days(from_date, to_date)
        target_per_day = (frappe.db.get_single_value('Worktime Settings', 'daily_hours') / 100) * degrees[0].degree
        target_time = (days - off_days) * target_per_day
    return target_time
    
def get_actual_time(from_date, to_date, user):
    employee = frappe.db.sql("""SELECT `name` FROM `tabEmployee` WHERE `user_id` = '{user}'""".format(user=user), as_dict=True)
    try:
        actual_time = frappe.db.sql("""SELECT SUM(`hours`) FROM `tabTimesheet Detail`
                                        WHERE DATE(`from_time`) >= '{from_date}' AND DATE(`from_time`) <= '{to_date}'
                                        AND `docstatus` = 1 AND `parent` IN (
                                            SELECT `name` FROM `tabTimesheet` WHERE `employee` = '{employee}'
                                        )""".format(from_date=from_date, to_date=to_date, employee=employee[0].name), as_list=True)[0][0]
        if not actual_time:
            actual_time = 0
    except:
        actual_time = 0
        
    # handle carryover and payouts
    employee = frappe.get_doc("Employee", employee[0].name)
    if employee.carryover_and_payouts:
        year = getdate(from_date).strftime("%Y")
        for cp in employee.carryover_and_payouts:
            if str(cp.year) == year:
                actual_time += cp.amount
                
    return actual_time

def get_holiday_balance(user, to_date):
    employee = frappe.db.sql("""SELECT `name` FROM `tabEmployee` WHERE `user_id` = '{user}'""".format(user=user), as_dict=True)
    leave_details = get_leave_details(employee[0].name, to_date)
    remaining_days = 0
    
    for key in leave_details["leave_allocation"]:
        remaining_days += int(leave_details["leave_allocation"][key]["remaining_leaves"])
    
    return remaining_days

def get_off_days(from_date, to_date):
    off_days = 0
    year = getdate(from_date).strftime("%Y")
    
    holiday_lists = frappe.db.sql("""SELECT `year`, `public_holiday_list` FROM `tabPublic Holiday List` WHERE `year` = '{year}' LIMIT 1""".format(year=year), as_dict=True)
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

def get_degrees(user):
    employee = frappe.db.sql("""SELECT `name` FROM `tabEmployee` WHERE `user_id` = '{user}'""".format(user=user), as_dict=True)
    degrees = frappe.db.sql("""SELECT `degree`, `date` FROM `tabEmployment Degree` WHERE `parent` = '{employee}' ORDER BY `date` ASC""".format(employee=employee[0].name), as_dict=True)
    return degrees
