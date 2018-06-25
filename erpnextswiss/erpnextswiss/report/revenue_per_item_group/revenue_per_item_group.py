# Copyright (c) 2013, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    columns = ["Item Group::200", "Amount:200", "Qty::150"]
    if filters:
        data = frappe.db.sql("""SELECT 
				  `t1`.`item_group`, 
				  SUM(`t1`.`base_amount`) AS `amount`, 
				  SUM(`t1`.`qty`) AS `qty`
				FROM `tabSales Invoice Item` AS `t1`
				LEFT JOIN `tabSales Invoice` AS `t2` ON `t1`.`parent` = `t2`.`name`
				WHERE 
				  `t2`.`docstatus` = 1
				  AND `t2`.`posting_date` >= "{0} 0:0" 
				  AND `t2`.`posting_date` <= "{1} 23:59"
				GROUP BY `t1`.`item_group`
				ORDER BY `t1`.`item_group` ASC;""".format(filters.from_date, filters.end_date), as_list = True)
    else:
        data = frappe.db.sql("""SELECT `t1`.`item_group`, 
				  SUM(`t1`.`base_amount`) AS `amount`, 
				  SUM(`t1`.`qty`) AS `qty`
				FROM `tabSales Invoice Item` AS `t1`
				LEFT JOIN `tabSales Invoice` AS `t2` ON `t1`.`parent` = `t2`.`name`
				WHERE `t2`.`docstatus` = 1
				GROUP BY `t1`.`item_group`
				ORDER BY `t1`.`item_group` ASC;""", as_list = True)
            
    return columns, data
