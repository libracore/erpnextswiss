# -*- coding: utf-8 -*-
# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.exceptions import PermissionError

@frappe.whitelist(allow_guest=True)
def get_pdf_as_guest(doctype, name, format=None, doc=None, no_letterhead=0, key=False):
    '''
        This function allows all guest users to download a specific PDF if the correct signature is known.
        
        :param key: must comply with the valid document signature
        
        All other params align with frappe.utils.print_format.download_pdf
        Callable with api/method/erpnextswiss.erpnextswiss.guest_print.get_pdf_as_guest?doctype={{ doctype }}&name={{ name }}&key={{ key }}
    '''
    if not key or key != frappe.get_doc(doctype, name).get_signature():
        raise PermissionError()
    
    frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = frappe.get_print(doctype, name, format, doc=doc, 
        as_pdf = True, no_letterhead=no_letterhead)
    frappe.local.response.type = "pdf"
