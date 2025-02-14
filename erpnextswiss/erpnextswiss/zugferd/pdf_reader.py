# -*- coding: utf-8 -*-
# Copyright (c) 2018-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#

import fitz
import frappe

# from PIL import Image
# import pytesseract

# Use with png-files
#def read_image(filename):
#    content_str = pytesseract.image_to_string(Image.open(filename), lang="deu")

def find_supplier_from_pdf(pdf_file, company=None, debug=False):
    # prepare supplier lists
    tax_ids, supplier_names = build_supplier_maps(company)
    
    # read pdf
    with fitz.open(pdf_file) as doc:
        content_string = ""
        for page in doc:
            content_string += page.get_text()
            
    # find by tax_id
    supplier_tax_id_hits = []
    _tax_id_hit = None
    for tax_id, supplier in tax_ids.items():
        if tax_id in content_string:
            if tax_id not in supplier_tax_id_hits:
                supplier_tax_id_hits.append(supplier)
                _tax_id_hit = tax_id
                
    if len(supplier_tax_id_hits) == 1:
        # one hit, accept this
        if debug:
            print("INFO: supplier {0} found based on tax id {1}".format(supplier_tax_id_hits[0], _tax_id_hit))
        return supplier_tax_id_hits[0]
        
    # find by supplier name
    supplier_name_hits = []
    _supplier_name_hit = None
    for supplier_name, supplier in supplier_names.items():
        if supplier_name in content_string:
            if supplier_name not in supplier_name_hits:
                supplier_name_hits.append(supplier)
                _supplier_name_hit = supplier_name
    
    if len(supplier_name_hits) == 1:
        # one hit, accept this
        if debug:
            print("INFO: supplier {0} found based on supplier name {1}".format(supplier_name_hits[0], _supplier_name_hit))
        return supplier_name_hits[0]
    
    if len(supplier_name_hits) == 0 and len(supplier_tax_id_hits) == 0:
        if debug:
            print("INFO: Neither tax id nor supplier name were found in this document")
        return None
        
    # try to cross-link
    double_hits = []
    for t in supplier_tax_id_hits:
        if t in supplier_name_hits:
            double_hits.append(t)
            
    if len(double_hits) == 1:
        if debug:
            print("INFO: Both tax id and supplier name match for {0}".format(double_hits[0]))
        return double_hits[0]
        
    # no unique supplier found, but some options... use first as a guess
    if len(supplier_tax_id_hits) > 0:
        if debug:
            print("INFO: Happy go lucky: first tax id used to match supplier {0} ({1})".format(supplier_tax_id_hits[0], supplier_tax_id_hits))
        return supplier_tax_id_hits[0]
    else:
        if debug:
            print("INFO: Happy go lucky: first supplier name matched supplier {0} ({1})".format(supplier_name_hits[0], supplier_name_hits))
        return supplier_name_hits[0]
    
def build_supplier_maps(company=None):
    if company:
        if type(company) == str:
            exclude_name = company
            exclude_tax_id = frappe.get_value("Company", company, "tax_id")
        else:
            frappe.throw("Please provide the company ID as a string as a parameter")
    else:
        exclude_name = None
        exclude_tax_id = None
        
    supplier_register = frappe.db.sql("""
        SELECT `name`, `supplier_name`
        FROM `tabSupplier`
        WHERE `disabled` = 0
          AND `supplier_name` IS NOT NULL
          AND `supplier_name` != "";
        """, as_dict=True)
        
    supplier_names = {}
    for s in supplier_register:
        if s['supplier_name'] not in supplier_names and s['supplier_name'] != exclude_name:
            supplier_names[s['supplier_name']] = s['name']
    
    tax_register = frappe.db.sql("""
        SELECT `name`, `tax_id`, `supplier_name`
        FROM `tabSupplier`
        WHERE `disabled` = 0
          AND `tax_id` IS NOT NULL
          AND `tax_id` != "";
        """, as_dict=True)
    
    tax_ids = {}
    for s in tax_register:
        if s['tax_id'] not in tax_ids and s['tax_id'] != exclude_tax_id:
            tax_ids[s['tax_id']] = s['name']
            
    return tax_ids, supplier_names
