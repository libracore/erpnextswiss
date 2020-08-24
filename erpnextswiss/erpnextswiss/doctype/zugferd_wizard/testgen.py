# -*- coding: utf-8 -*-
# Copyright (c) 2019-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import os
from erpnextswiss.erpnextswiss.zugferd.zugferd import get_xml, get_content_from_zugferd
from erpnextswiss.erpnextswiss.doctype.zugferd_wizard.zugferd_wizard import get_inv




@frappe.whitelist()
def create_supplier():
    frappe.msgprint("Hallo")
    
    invoice = get_inv()
    
    doc = frappe.get_doc({
            'doctype': 'Supplier',
            'title': seller.find('ram:name').string,
            'supplier_name': seller.find('ram:name').string,
            'tax_id': seller.find('ram:id').string,
            'supplier_group': "All Supplier Groups" #supplier_group
        })
    doc.insert()
    
    frappe.msgprint("<b>" + "Added new supplier: " + "</b>" + "<br>" + "<br>" + "<b>" + "Title: " + "</b>" 
    + doc.title + "<br>" + "<b>" + "Supplier Name: " "</b>" + doc.supplier_name + "<br>" + "<b>" + "Global ID: " 
    + "</b>" + doc.global_id + "<br>" + "<b>" + "Supplier Group: " + "</b>" + doc.supplier_group + "<br>")
    
    #INSERTION
    address_doc = frappe.get_doc({
        'doctype': 'Address',
        'address_title': doc.supplier_name + " address",
        'pincode': seller.find('ram:postcodecode').string,
        'address_line1': seller.find('ram:lineone').string,
        'city': 'zürich', #seller.find('ram:cityname').string or "",
        'links': [ {'link_doctype': 'Supplier', 'link_name': doc.supplier_name} ]
        #'country': "Schweiz" #seller.find('ram:CountryID').string or ""
    })
    address_doc.insert()
