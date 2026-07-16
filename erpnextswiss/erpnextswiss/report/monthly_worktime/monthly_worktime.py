# Copyright (c) 2021-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
import datetime, calendar
from erpnextswiss.scripts.worktime_utils import get_worktime_overview

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Day"), "fieldname": "day", "fieldtype": "Date", "width": 80},
        {"label": _("Working Hours"), "fieldname": "working_hours", "fieldtype": "Float", "precision": 2, "width": 120},
        {"label": _("Work Start"), "fieldname": "work_start", "fieldtype": "Data", "width": 170},
        {"label": _("Work End"), "fieldname": "work_end", "fieldtype": "Data", "width": 170},
        {"label": _("Breaks"), "fieldname": "breaks", "fieldtype": "Data", "width": 150},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 150},
        {"label": _(" "), "fieldname": "blank", "width": 20}
    ]

def get_data(filters):
    # get all days
    num_days = calendar.monthrange(filters.year, filters.month)[1]
    days = [datetime.date(filters.year, filters.month, day) for day in range(1, num_days+1)]

    # take off-time from activity determination
    off_types = []
    for t in frappe.db.sql("""
        SELECT `activity_type` 
        FROM `tabActivity Type Determination`
        WHERE `company` = "{company}";""".format(company=filters.company), as_dict=True):
        off_types.append(t['activity_type'])
    
    # expand all days
    data = []
    total_working_hours = 0
    for day in days:
        sql_query = """
            SELECT
                `tabTimesheet Detail`.`hours`,
                `tabTimesheet Detail`.`from_time`,
                `tabTimesheet Detail`.`to_time`,
                `tabTimesheet Detail`.`activity_type`
            FROM `tabTimesheet Detail`
            WHERE `tabTimesheet Detail`.`name` IN (
                SELECT `tLookup`.`name`
                FROM `tabTimesheet Detail` AS `tLookup`
                LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tLookup`.`parent`
                WHERE 
                    `tabTimesheet`.`docstatus` = 1
                    AND `tabTimesheet`.`employee` = "{employee}"
                    AND DATE(`tLookup`.`from_time`) = "{date}"
            )
            ORDER BY `tabTimesheet Detail`.`from_time` ASC;""".format(
                employee=filters.employee, date=day)
        
        blocks = frappe.db.sql(sql_query, as_dict=True)
        
        working_hours = 0
        remarks = None
        breaks = []
        if blocks and len(blocks) > 0:
            # has worked here, compile
            work_start = blocks[0]['from_time']
            work_end = blocks[-1]['to_time']
            for block in blocks:
                if block['activity_type'] not in off_types:
                    working_hours += float(block['hours'])
            remarks = blocks[0]['activity_type']
            # find breaks
            if len(blocks) > 1:
                for i in range(1, len(blocks)):
                    break_span = blocks[i]['from_time'] - blocks[i - 1]['to_time']
                    break_in_minutes = break_span.total_seconds() / 60
                    if break_in_minutes >= 5:
                        break_text = "{minutes:d}' @ {time}".format(minutes=int(break_in_minutes), time=blocks[i-1]['to_time'].strftime("%H:%M"))
                        breaks.append(break_text)
        else:
            work_start = None
            work_end = None
        
        # for holidays, try to fetch remarks from holiday list
        if not remarks:
            holidays = frappe.db.sql("""
                SELECT `description` 
                FROM `tabHoliday` 
                WHERE `parenttype` = "Holiday List"
                  AND `parentfield` = "holidays"
                  AND `holiday_date` = "{day}";""".format(day=day), as_dict=True)
            if len(holidays) > 0:
                remarks = holidays[0]['description']
                
        total_working_hours += working_hours
        data.append({
            'day': day,
            'work_start': work_start,
            'work_end': work_end,
            'working_hours': working_hours,
            'remarks': remarks,
            'breaks': ", ".join(breaks)
        })
    
    # totals
    worktime_overview = get_worktime_overview(filters.employee, filters.company, datetime.date(filters.year, filters.month, 1), datetime.date(filters.year, filters.month, num_days))
    target_hours = flt(worktime_overview.get('target_time'), 2)
    actual_time = flt(worktime_overview.get('actual_time'), 2)
    monthly_overtime = flt(worktime_overview.get('overtime'), 2)
    holiday_hours_check = worktime_overview.get('holiday_hours_check')
    holidays_in_hours = flt(worktime_overview.get('holidays_in_hours'), 2)
    opening_balance = flt(worktime_overview.get('opening_balance'), 2)
    closing_balance = flt(worktime_overview.get('closing_balance'), 2)
    total_working_hours = flt((worktime_overview.get('actual_time') + worktime_overview.get('holidays_in_hours')), 2)
    warning = 'Keine'
    
    if holiday_hours_check:
        summary = holiday_hours_check.get("summary", {})

        invalid_days = summary.get("number_of_invalid_days", 0)
        deviation = summary.get("deviation_hours", {})

        if invalid_days:
            deviation_min = deviation.get("min")
            deviation_max = deviation.get("max")

            if deviation_min == deviation_max:
                warning = _("{0} fehlerhafte Ferientage; Abweichung: {1} Std.").format(invalid_days, deviation_min)
            else:
                warning = _("{0} fehlerhafte Ferientage; Abweichung: {1} bis {2} Std.").format(invalid_days, deviation_min, deviation_max)
        
    data.append({
        'working_hours': actual_time,
        'work_start': _("Working hours")
    })

    data.append({
        'working_hours': holidays_in_hours,
        'work_start': _("Holidays in hours")
    })

    data.append({
        'working_hours': total_working_hours,
        'work_start': _("Total"),
        'work_end': _("Target: {0} h").format(target_hours)
    })
    
    data.append({
        'work_start': _("Opening Balance"),
        'work_end': opening_balance
    })

    data.append({
        'work_start': _("Difference in hours"),
        'work_end': monthly_overtime
    })
    
    data.append({
        'work_start': _("Closing Balance"),
        'work_end': closing_balance
    })
    
    data.append({
        'work_start': _("Warnings"),
        'work_end': warning,
        'breaks': frappe.get_value("Employee", filters.employee, "employee_name")
    })

    return data
