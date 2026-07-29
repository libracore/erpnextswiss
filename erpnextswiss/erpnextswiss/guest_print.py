# -*- coding: utf-8 -*-
# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe.www.printview import validate_key

@frappe.whitelist(allow_guest=True)
def get_pdf_as_guest(doctype, name, format=None, doc=None, no_letterhead=0, key=False):
    """Download a PDF using Frappe's random, optionally expiring share key."""
    document = frappe.get_doc(doctype, name)
    validate_key(str(key or ""), document)

    frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = frappe.get_print(
        doctype,
        name,
        format,
        doc=doc,
        as_pdf=True,
        no_letterhead=no_letterhead,
    )
    frappe.local.response.type = "pdf"
