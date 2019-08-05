# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#
#
#
import frappe
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
from facturx import generate_facturx_from_binary


"""
Creates an XML file from a sales invoice

:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_pdf(sales_invoice_name, verify=True, format=None, doc=None, no_letterhead=0):
    try:
   
        doctype = "Sales Invoice"
        html = frappe.get_print(doctype, sales_invoice_name, format, doc=doc, no_letterhead=no_letterhead)
	
        pdf = get_pdf(html)
        xml = create_zugferd_xml(sales_invoice_name)
    
        facturx_pdf = generate_facturx_from_binary(pdf, xml)
         
        return facturx_pdf
    except Exception as err:
        return "Unable to create zugferdPDF: {0}".format(err)


@frappe.whitelist()
def download_zugferd_pdf(sales_invoice_name, format=None, doc=None, no_letterhead=0, verify=True):
    frappe.local.response.filename = "{name}.pdf".format(name=sales_invoice_name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = create_zugferd_pdf(sales_invoice_name, verify, format, doc, no_letterhead)
    frappe.local.response.type = "download"
    return
    
 
