# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    columns = ["Project::200", "Hours"]
    if filters:
        data = frappe.db.sql("""SELECT `project` AS `Project`, SUM(`hours`) AS `Hours`
            FROM `tabTimesheet Detail` 
            LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
            WHERE `tabTimesheet`.`docstatus` = 1 AND `from_time` > "{0} 0:0" AND `from_time` < "{1} 23:59"
            GROUP BY `Project`
            ORDER BY `Hours` DESC""".format(filters.from_date, filters.end_date), as_list = True)
    else:
        data = frappe.db.sql("""SELECT `project` AS `Project`, SUM(`hours`) AS `Hours`
            FROM `tabTimesheet Detail` 
            LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
            WHERE `tabTimesheet`.`docstatus` = 1
            GROUP BY `Project`
            ORDER BY `Hours` DESC""".format(filters.from_date, filters.end_date), as_list = True)
                    
    return columns, data
