# -*- coding: utf-8 -*-
# Copyright (c) 2018-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#
#
#
import frappe, os
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
#from facturx import generate_facturx_from_binary, get_facturx_xml_from_pdf, check_facturx_xsd, generate_facturx_from_file
from erpnextswiss.erpnextswiss.zugferd.facturx.facturx import generate_facturx_from_binary, get_facturx_xml_from_pdf, check_facturx_xsd
from bs4 import BeautifulSoup
from frappe.utils.file_manager import save_file
from pathlib import Path
import unicodedata
from PyPDF2 import PdfFileWriter
import xml.etree.ElementTree as ET
import xml.etree.ElementTree
from xml.etree import ElementTree
from lxml import etree
from io import BytesIO
import datetime
from datetime import date

"""
Creates a ZUGFeRD file from a sales invoice

:params:docname:         document name of the sale invoice
:params:verify:          verify xml content (default True)
:params:format:          print format to use (default None/default)
:params:doc:             document record of the sale invoice
:params:doctype:         target doctype (default Sales Invoice)
:params:no_letterhead:   disable letterhead (default 0)
:returns:                ZUGFeRD pdf
"""
def create_zugferd_pdf(docname, verify=True, format=None, doc=None, doctype="Sales Invoice", no_letterhead=0):
    try:       
        html = frappe.get_print(doctype, docname, format, doc=doc, no_letterhead=no_letterhead)
        pdf = get_pdf(html)
        xml = create_zugferd_xml(docname)
        facturx_pdf = generate_facturx_from_binary(pdf, xml.encode('utf-8'))  ## Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
        return facturx_pdf
    except Exception as err:
        frappe.log_error("Unable to create zugferdPDF: {0}\n{1}".format(err, xml), "ZUGFeRD")
        # fallback to normal pdf
        pdf = get_pdf(html)
        return pdf

@frappe.whitelist()    
def get_xml(path):
    xml_filename, xml_content = get_facturx_xml_from_pdf(path)
    return xml_content

"""
Extracts the relevant content for a purchase invoice from a ZUGFeRD XML
:params:zugferd_xml:    xml content (string)
:return:                simplified dict with content
"""
def get_content_from_zugferd(zugferd_xml, debug=False):
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {}
  
    # seller information
    seller = soup.find('ram:sellertradeparty')
    invoice['supplier_name'] = seller.find('ram:name').string
    invoice['supplier_taxid'] = seller.find('ram:id').string
    
    supplier_match_by_tax_id = frappe.get_all("Supplier", 
                                filters={'tax_id': invoice['supplier_taxid']},
                                fields=['name'])
    if len(supplier_match_by_tax_id) > 0:
        # matched by tax id
        invoice['supplier'] = supplier_match_by_tax_id[0]['name']
    else:
        supplier_match_by_name = frappe.get_all("Supplier", 
                                    filters={'supplier_name': invoice['supplier_name']},
                                    fields=['name'])   
        if len(supplier_match_by_name) > 0:
            # matched by supplier name
            invoice['supplier'] = supplier_match_by_name[0]['name']   
        else:
            # need to insert new supplier
            invoice['supplier'] = None
    
    # find due date
    today = date.today()
    d3 = today.strftime("%Y-%m-%d")
    invoice['due_date'] = d3
    try:        
        date_str = soup.find('ram:duedatedatetime').string
        invoice['due_date'] = datetime.datetime.strptime(date_str, '%Y%m%d').strftime('%d-%m-%Y')
    except:
        # use default as due date
        pass

    document_context = soup.find('rsm:exchangeddocument')
    invoice['terms'] = document_context.find('ram:content').string
    
    doc_id = document_context.find('ram:id').string
    invoice['bill_no'] = doc_id
    
    specified_payment_terms = soup.find('ram:specifiedtradepaymentterms') 
    description =  specified_payment_terms.find('ram:description').string
  
    invoice['currency'] = soup.find('ram:invoicecurrencycode').string
    
    applicable_tax = soup.find('ram:applicabletradetax')
    tax_rate = applicable_tax.find('ram:rateapplicablepercent').string
    invoice['tax_rate'] = tax_rate
    # find tax template matching the rate
    tax_template_match = frappe.get_all("Purchase Taxes and Charges",
                                        filters={'rate': tax_rate},
                                        fields=['parent'])
    if len(tax_template_match) > 0:
        invoice['tax_template'] = tax_template_match[0]['parent']
    else:
        invoice['tax_template'] = None

    # collect items
    items = []
    for item in soup.find_all('ram:includedsupplychaintradelineitem'):
        _item = {
            'net_price': soup.find('ram:netpriceproducttradeprice'),
            'qty': soup.find('ram:billedquantity'),
            'seller_item_code': item.find('ram:sellerassignedid').string,
            'item_name': item.find('ram:name').string
        }
        
        # match by seller item code
        match_item_by_code = frappe.get_all("Item",
                                            filters={'item_code': _item['seller_item_code']},
                                            fields=['name'])
        if len(match_item_by_code) > 0: 
            _item['item_code'] = match_item_by_code[0]['name']
        else:
            # match by item name
            match_item_by_name = frappe.get_all("Item",
                                                filters={'item_name': _item['item_name']},
                                                fields=['name'])
            if len(match_item_by_name) > 0: 
                _item['item_code'] = match_item_by_name[0]['name']
            else:
                # no match      
                _item['item_code'] = None
        
        items.append(_item)
    invoice['items'] = items

    return invoice

    

