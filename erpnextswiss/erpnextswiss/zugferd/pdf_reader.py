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

def find_supplier_from_pdf(pdf_file):
    # prepare supplier lists
    tax_ids, supplier_names = build_supplier_maps()
    
    # read pdf
    with fitz.open(pdf_file) as doc:
        content_string = ""
        for page in doc:
            content_string += page.get_text()
            
    # find by tax_id
    supplier_tax_id_hits = []
    for tax_id, supplier in tax_ids.items():
        if tax_id in content_string:
            if tax_id not in supplier_tax_id_hits:
                supplier_tax_id_hits.append(supplier)
                
    if len(supplier_tax_id_hits) == 1:
        # one hite, accept this
        return supplier_tax_id_hits[0]
        
    # find by supplier name
    supplier_name_hits = []
    for supplier_name, supplier in supplier_names.items():
        if supplier_name in content_string:
            if supplier_name not in supplier_name_hits:
                supplier_name_hits.append(supplier)
    
    if len(supplier_name_hits) == 1:
        # one hite, accept this
        return supplier_name_hits[0]
    
    if len(supplier_name_hits) == 0 and len(supplier_tax_id_hits) == 0:
        return None
        
    # try to cross-link
    double_hits = []
    for t in supplier_tax_id_hits:
        if t in supplier_name_hits:
            double_hits.append(t)
            
    if len(double_hits) == 1:
        return double_hits[0]
        
    # no unique supplier found, but some options... use first as a guess
    if len(supplier_tax_id_hits) > 0:
        return supplier_tax_id_hits[0]
    else:
        return supplier_name_hits[0]
    
def build_supplier_maps():
    suppliers = frappe.db.sql("""
        SELECT `name`, `tax_id`, `supplier_name`
        FROM `tabSupplier`
        WHERE `disabled` = 0
          AND `tax_id` IS NOT NULL
          AND `supplier_name` IS NOT NULL;
        """, as_dict=True)
        
    tax_ids, supplier_names = {}, {}
    for s in suppliers:
        if s['supplier_name'] not in tax_ids:
            supplier_names[s['supplier_name']] = s['name']
        if s['tax_id'] not in tax_ids:
            tax_ids[s['tax_id']] = s['name']
    
    return tax_ids, supplier_names
