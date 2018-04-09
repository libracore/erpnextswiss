# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    columns = ["Activity::200", "Hours"]
    if filters:
        data = frappe.db.sql("""SELECT `activity_type` AS `Activity`, SUM(`hours`) AS `Hours`
            FROM `tabTimesheet Detail` 
            WHERE `from_time` > "{0} 0:0" AND `from_time` < "{1} 23:59"
            GROUP BY `Activity`
            ORDER BY `Hours` DESC""".format(filters.from_date, filters.end_date), as_dict = True)
    else:
        data = frappe.db.sql("""SELECT `activity_type` AS `Activity`, SUM(`hours`) AS `Hours`
            FROM `tabTimesheet Detail` 
            GROUP BY `Activity`
            ORDER BY `Hours` DESC""".format(filters.from_date, filters.end_date), as_dict = True)
            
    return columns, data
