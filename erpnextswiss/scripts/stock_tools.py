# -*- coding: utf-8 -*-
#
# stock_tools.py
#
# Copyright (C) libracore, 2017-2019
# https://www.libracore.com or https://github.com/libracore
#
# For information on ERPNext, refer to https://erpnext.org/
#
# Execute with $ bench execute erpnextswiss.scripts.stock_tools.<function>
#

import frappe
import re

def submit_stock_entry(name):
    record = frappe.get_doc("Stock Entry", name)
    record.submit()
    frappe.db.commit()
    return
