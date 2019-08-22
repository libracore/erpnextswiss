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
from facturx import generate_facturx_from_binary, get_facturx_xml_from_pdf
from bs4 import BeautifulSoup

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
    
@frappe.whitelist()
def make_pinv(input_file):
    extracted_xml = get_facturx_xml_from_pdf(input_file, check_xsd=True)
    frappe.msgprint(extracted_xml)
    return extracted_xml
 

"""
Extracts the relevant content for a purchase invoice from a ZUGFeRD XML
:params:zugferd_xml:    xml content (string)
:return:                simplified dict with content
"""
def get_content_from_zugferd(zugferd_xml, debug=False):
    # create soup object
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {}
    
    
    if suppliers_global_id:
        global_id_xml = soup.SpecifiedTradeProduct.GlobalID.get_text()
        suppliers_global_id = frappe.get_all('Supplier', filters={'supplier': global_id_xml}, fields = supplier_name[0])        
        invoice['supplier_name'] = soup.sellertradeparty.name.get_text()
        frappe.printmsg("Name of supplier is" + global_id_xml)
    elif suppliers_tax:
        tax_id_xml = soup.find_all(schemeID='VA')
        suppliers_tax = frappe.get_all('Supplier', filters={'supplier': tax_id_xml[0]}, fields = supplier_name[0])
        supplier = frappe.get_doc('Supplier', 'suppliers tax')       
        invoice['supplier_name'] = soup.sellertradeparty.name.get_text()
        supplier.global_id = soup.SpecifiedTradeProduct.GlobalID.get_text()
        supplier.save()
    else:
        tax_id_list = soup.find_all(schemeID='VA')
        # insert a new Suppler:
        frappe.db.insert({
        doctype: 'Supplier',
        supplier_name: soup.sellertradeparty.name.get_text(),
        tax_id: tax_id_list[0],
        global_id: soup.SpecifiedTradeProduct.GlobalID.get_text()
    })
    

    
    # get article information (items)
    invoice['items'] = soup.sellertradeparty.name.get_text()
    
    # dates (codes: UNCL 2379: 102=JJJJMMTT, 610=JJJJMM, 616=JJJJWW)
    try:
        invoice['posting_date'] = datetime.strptime(
            soup.issuedatetime.datetimestring.get_text(), "%Y%m%d")
    except Exception as err:
        if debug:
            print("Read posting date failed: {err}".format(err=err))
        pass
    return invoice
