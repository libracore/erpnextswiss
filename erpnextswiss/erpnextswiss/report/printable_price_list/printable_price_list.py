# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    columns = ["Item Code:Link/Item:200", "Item Name::200", "Item Group:Link/Item Group:200", "Amount:Currency:200"]
    if filters:
        data = frappe.db.sql("""SELECT `t1`.`item_code`, 
				  `t1`.`item_name`, 
				  `t2`.`item_group`,
				  `t1`.`price_list_rate`
				FROM `tabItem Price` AS `t1`
				LEFT JOIN `tabItem` AS `t2` ON `t1`.`item_code` = `t2`.`item_code`
				WHERE `price_list` = '{0}'
				ORDER BY `t1`.`item_code` ASC;""".format(filters.price_list), as_list = True)
    else:
        data = frappe.db.sql("""SELECT `t1`.`item_code`, 
				  `t1`.`item_name`, 
				  `t2`.`item_group`,
				  `t1`.`price_list_rate`
				FROM `tabItem Price` AS `t1`
				LEFT JOIN `tabItem` AS `t2` ON `t1`.`item_code` = `t2`.`item_code`
				ORDER BY `t1`.`item_code` ASC;""", as_list = True)
            
    return columns, data
