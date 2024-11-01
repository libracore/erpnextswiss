# -*- coding: utf-8 -*-
#
# item_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
#
# Execute with $ bench execute erpnextswiss.scripts.item_tools.<function>
#

import frappe
import re

@frappe.whitelist()
def get_next_item_code():
	prefix = None
	last_item_code = frappe.db.sql("""SELECT `name` FROM `tabItem` ORDER BY CAST(`name` AS int) DESC LIMIT 1""", as_dict=True)
	#Check if already an item exist
	if last_item_code:
		last_item_code = str(last_item_code[0].name)
		last_item_code_len = len(last_item_code.split("-"))
		if last_item_code_len > 1:
			last_item_code = last_item_code.split("-")[last_item_code_len - 1]
			prefix = last_item_code.replace(last_item_code.split("-")[last_item_code_len - 1], "")
			new_item_code = int(last_item_code) + 1
			new_item_code = prefix + str(new_item_code)
		else:
			new_item_code = int(last_item_code) + 1
		return new_item_code
		
	else:
		return 1
		
@frappe.whitelist()
def get_voucher_value(voucher_code, customer):
    sql_query = u"""SELECT 
                    (IFNULL(SUM(`qty` * `base_rate`), 0)) AS `value`
                FROM `tabSales Invoice Item` 
                WHERE 
                    `item_code` = '{voucher}'
                    AND `parent` IN (SELECT `name` FROM `tabSales Invoice` WHERE `docstatus` = 1 AND `customer` = '{customer}');""".format(voucher=voucher_code,customer=customer)
    value = frappe.db.sql(sql_query, as_dict=True)
    if value:
        return { 'value': value[0].value }
    else:
        return { 'value': 0 }
