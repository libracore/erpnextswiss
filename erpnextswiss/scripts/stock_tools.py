# -*- coding: utf-8 -*-
#
# stock_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
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
