# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from datetime import datetime, timedelta

def get_working_days_in_current_year(holiday_list):
    from_date = datetime(datetime.now().year, 1, 1)
    to_date = datetime.now()
    return get_working_days_between_dates(holiday_list, from_date, to_date)
    
def get_working_days_between_dates(holiday_list, from_date, to_date, debug=False):
    # check parameters
    if type(from_date) is str:
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
    if type(to_date) is str:
        to_date = datetime.strptime(to_date, "%Y-%m-%d")
    # prepare
    holidays = get_holidays(holiday_list)
    date = from_date
    days = 0
    # loop through date range
    while (date <= to_date):
        # check if current day is a working day
        if "{y:04}-{m:02}-{d:02}".format(y=date.year, m=date.month, d=date.day) not in holidays:
            days += 1
        date = date + timedelta(days=1)
    return days

def get_holidays(holiday_list):
    sql_query = """SELECT `holiday_date` FROM `tabHoliday` WHERE `parent` = "{h}";""".format(h=holiday_list)
    data = frappe.db.sql(sql_query, as_dict=True)
    dates = []
    for d in data:
        dates.append(d['holiday_date'].strftime("%Y-%m-%d"))
    return dates
