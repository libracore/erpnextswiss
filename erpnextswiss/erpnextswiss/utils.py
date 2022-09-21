# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore, Fink Zeitsysteme and contributors
# For license information, please see license.txt
#

# imports
import frappe
from frappe import _

def has_attachments(dn, dt=None):
    if dt:
        files = frappe.get_all("File", filters={'attached_to_name': dn, 'attached_to_doctype': dt}, fields=['name'])
    else:
        files = frappe.get_all("File", filters={'attached_to_name': dn}, fields=['name'])
    if len(files) > 0:
        return True
    else:
        return False
        
def get_numeric_part(s):
    if not s:
        return "0"
    num = ""
    for c in (s or ""):
        if c.isdigit():
            num = num + c
    if num == "":
        return "0"
    else:
        return num
