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

"""
Creates an XML file from a sales invoice

:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_pdf(docname, verify=True, format=None, doc=None, doctype="Sales Invoice", no_letterhead=0):
    try:       
        html = frappe.get_print(doctype, docname, format, doc=doc, no_letterhead=no_letterhead)
        pdf = get_pdf(html)
        xml = create_zugferd_xml(docname)
        
        #facturx_pdf = generate_facturx_from_file(file, xml)  
        ## The second argument of the method generate_facturx must be either a string, an etree.Element() object or a file (it is a <class 'bytes'>).
        facturx_pdf = generate_facturx_from_binary(pdf, xml.encode('utf-8'))  ## Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
        
        return facturx_pdf
    except Exception as err:
        frappe.log_error("Unable to create zugferdPDF: {0}\n{1}".format(err, xml), "ZUGFeRD")
        # fallback to normal pdf
        pdf = get_pdf(html)
        return pdf

@frappe.whitelist()
def download_zugferd_pdf(docname, doctype="Sales Invoice", format=None, no_letterhead=0, verify=True):
    frappe.local.response.filename = "{name}.pdf".format(name=docname.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = create_zugferd_pdf(docname, verify, format, no_letterhead)
    html = frappe.get_print(doctype, sales_invoice_name, format, doc=doc, no_letterhead=no_letterhead)
    frappe.local.response.filecontent = get_pdf(html)
    frappe.local.response.type = "download"
    return 
    
@frappe.whitelist() 
def import_pdf(content):
    # using readAsBinaryString
    #content_bytes = BytesIO(content.encode('utf8'))
    #f = open("/tmp/test.pdf", 'w')
    #f.write(content)
    #content_bytes = bytes(content, 'utf8')
    #f = open("/tmp/test.pdf", 'wb')
    #f.write(content_bytes)   
    xml_content=content
    #xml_filename, xml_content = get_facturx_xml_from_pdf(content_bytes)
    #check_facturx_xsd(xml_content)
    #frappe.msgprint(xml_content.decode('utf-8'))
    #frappe.msgprint("XML: {0}".format(xml_content))
    return xml_content

#this is the method that does not work
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
    # create soup object
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {}
    
    # seller information
    seller = soup.find('ram:sellertradeparty')
    invoice['supplier_name'] = seller.find('ram:name').string
    
    # get article information (items)
    #TODO invoice['items'] = soup.sellertradeparty.name.get_text()
    
    # dates (codes: UNCL 2379: 102=JJJJMMTT, 610=JJJJMM, 616=JJJJWW)
    try:
        invoice['posting_date'] = datetime.strptime(
            soup.issuedatetime.datetimestring.get_text(), "%Y%m%d")
    except Exception as err:
        if debug:
            print("Read posting date failed: {err}".format(err=err))
        pass
    return invoice

    #this works to add a new document into existing doctype    
    #duplicate doctypes will not be added

@frappe.whitelist()
def gen():
    
    frappe.msgprint("hallo ")
    doc = frappe.get_doc({
    'doctype': 'Supplier',
    'title': 'New Supplier',
    'supplier_name': 'Benjamin ehrer',
    'global_id': 'ID: 69',
    'supplier_group': 'Services' 
    })
    doc.insert()
    
    frappe.msgprint("Found supplier: " +  doc.supplier_name + "\n with details")
    
    return 
    
def con(zugferd_xml): 
    content = []
    # Read the XML file
    with open(zugferd_xml, "r") as file:
    # Read each line in the file, readlines() returns a list of lines
        content = file.readlines()
        # Combine the lines in the list into a string
        content = "".join(content)
        bs_content = bs(content, "lxml")
        result = ID.get("name")
        print(result)

    return
    
def test_content(zugferd_xml, debug=False):
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {}

        #todo add dict entries if suppliert exists; should/could be 
        
        # add address of n ew supplier to address doctype
    address_doc = frappe.get_doc({
        'doctype': 'Address',
        'title': soup.sellertradeparty.name.get_text() + " address",
        'pincode': soup.PostalTradeAddress.PostCodeCode.get_text(),
        'address_line1': soup.PostalTradeAddress.LineOne.get_text(),
        'city': soup.PostalTradeAddress.CityName.get_text(),
        'country': soup.PostalTradeAddress.CountryID.get_text()
    })
    doc.insert()
        
    #add supplier address doc to dict
    invoice['supplier_addressline1'] = soup.PostalTradeAddress.LineOne.get_text(),
    #todo add dict entries if suppliert exists; should/could be optimized to reduce duplicate code
       
    
    # insert a new Supplier document:
    doc = frappe.get_doc({
        'doctype': 'Supplier',
        'title': soup.sellertradeparty.name.get_text(),
        'supplier_name': soup.sellertradeparty.name.get_text(),
        'global_id': 'ID: ?',
        'tax_id': tax_id_list[0],
        'supplier_group': supplier_group
    })
    doc.insert()
        
    #add supplier information doc to dict
    invoice['supplier_name'] = soup.sellertradeparty.name.get_text()

    # screen information to show what got added, whot was found in pdf, and what will be generated new
    frappe.msgprint("Added new Supplier: "  + doc.supplier_name + "to System with information")
        
    frappe.msgprint("Title: "  + doc.supplier_name )
    frappe.msgprint("Supplier Name: "  + doc.supplier_name)
    frappe.msgprint("Global ID: "  + doc.global_id )
    frappe.msgprint("Supplier Group: "  + doc.supplier_group )
    frappe.msgprint("Added address for new Supplier: "  + doc.supplier_group )
    frappe.msgprint("Address Line: "  + address_doc.address_line1)
    frappe.msgprint("City: "  + address_doc.city )
    frappe.msgprint("Country: "  + address_doc.country )
    frappe.msgprint("Pincode "  + address_doc.pincode )
        
     
    return invoice


