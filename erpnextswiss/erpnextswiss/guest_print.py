# -*- coding: utf-8 -*-
# Copyright (c) 2013, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe.rate_limiter import rate_limit
from frappe.www.printview import validate_key
from .print_format_safety import _normalize_no_letterhead


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60 * 60, methods="GET", ip_based=True)
def get_pdf_as_guest(doctype, name, format=None, doc=None, no_letterhead=0, key=False):
    """Download a PDF using Frappe's random, optionally expiring share key."""
    document = frappe.get_doc(doctype, name)
    validate_key(str(key or ""), document)
    no_letterhead = _normalize_no_letterhead(no_letterhead)

    frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = frappe.get_print(
        doctype,
        name,
        format,
        # Never render caller-supplied document JSON for a public share link.
        doc=None,
        as_pdf=True,
        no_letterhead=no_letterhead,
    )
    frappe.local.response.type = "pdf"
