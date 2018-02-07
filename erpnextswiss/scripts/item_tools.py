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
def get_next_item_code():
	#This function is used to automatically create a new item code that is 1 higher than the last one created.
	
	#get last created Item Code
	last_item_code = frappe.db.sql("SELECT item_code FROM tabItem ORDER BY creation DESC LIMIT 1", as_dict=True)
	
	#Get numeric part of item code for increase with regex
	pattern = re.compile("(\w*)(\d+)")
	last_item_code_clean = pattern.findall((last_item_code[0]["item_code"]))
	
	#increase numeric item code with 1 and add prefix (if avaible)
	next_item_code = str(last_item_code_clean[-1][0]) + str(int(last_item_code_clean[-1][1]) + 1)
	
	return next_item_code