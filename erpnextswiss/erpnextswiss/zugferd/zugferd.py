# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#


import frappe
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
from facturx import generate_facturx_from_binary, get_facturx_xml_from_pdf, check_facturx_xsd, generate_facturx_from_file

"""
Creates an XML file from a sales invoice
:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_pdf(docname, verify=True, format=None, doc=None, doctype="Sales Invoice", no_letterhead=0):
    xml = None
    try:
        html = frappe.get_print(doctype, docname, format, doc=doc, no_letterhead=no_letterhead)
        try:
            pdf = get_pdf(html, print_format=format)
        except:
            # this is a fallback to Frappe ERPNext that does not support dynamic print format options (such as smart shrinking)
            pdf = get_pdf(html)
            
        xml = create_zugferd_xml(docname)
        
        if xml: 
            facturx_pdf = generate_facturx_from_binary(pdf, xml.encode('utf-8'))  ## Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
            return facturx_pdf
        else:
            # failed to generate xml, fallback
            return get_pdf(html)
    except Exception as err:
        frappe.log_error("Unable to create zugferdPDF for {2}: {0}\n{1}".format(err, xml, docname), "ZUGFeRD")
        # fallback to normal pdf
        return get_pdf(html)

@frappe.whitelist()
def download_zugferd_pdf(sales_invoice_name, format=None, doc=None, no_letterhead=0, verify=True):
    frappe.local.response.filename = "{name}.pdf".format(name=sales_invoice_name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = create_zugferd_pdf(sales_invoice_name, verify=verify, format=format, doc=doc, no_letterhead=no_letterhead)
    frappe.local.response.type = "download"
    return
