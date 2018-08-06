#
# item_tools.py
#
# Copyright (C) libracore, 2017
# https://www.libracore.com or https://github.com/libracore
#
# For information on ERPNext, refer to https://erpnext.org/
#
# Execute with $ bench execute erpnextswiss.scripts.item_tools.<function>
#

import frappe
import re

@frappe.whitelist()
def get_next_item_code(start_value="1"):
	#This function is used to automatically create a new item code that is 1 higher than the last one created.
	
	#get last created Item Code
	last_item_code = frappe.db.sql("SELECT item_code FROM tabItem ORDER BY creation DESC LIMIT 1", as_dict=True)

	#Check if already an item exist
	if last_item_code:
		#Get numeric part of item code for increase with regex
		pattern = re.compile("(\D*)(\d+)")
		last_item_code_clean = pattern.findall((last_item_code[0]["item_code"]))
		
		#increase numeric item code with 1 and add prefix (if avaible)
		next_item_code = str(last_item_code_clean[0][0]) + str(int(last_item_code_clean[0][1]) + 1)
	
		return next_item_code
		
	#if its the first item, return start value
	return start_value
    
@frappe.whitelist()
def get_voucher_value(voucher_code, customer):
    sql_query = """SELECT 
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
