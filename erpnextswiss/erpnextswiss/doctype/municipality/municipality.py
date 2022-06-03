# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import csv
from frappe.utils.background_jobs import enqueue

class Municipality(Document):
    pass

@frappe.whitelist()
def enqueue_import_municipality(content):
    kwargs={
          'content': content
        }
    
    enqueue("erpnextswiss.erpnextswiss.doctype.municipality.municipality.import_municipality",
        queue='long',
        timeout=15000,
        **kwargs)
    return {'result': _('Import started...')}

def import_municipality(content):   
    isfirst = True
    field_index = {}
    # read csv
    elements = csv.reader(content.splitlines(), dialect=csv.excel)
    # process elements
    for element in elements:
        if isfirst:
            isfirst = False;
            # loop through cells
            for i in range(0, len(element)):
                field_index[element[i].lower()] = i
            continue
        # check if the municipality is already in the database
        db_municipality = frappe.get_all("Municipality", 
            filters={'bfsnr': element[field_index['bfsnr']]}, 
            fields=['name'])
        if not db_municipality:
            # municipality is not in the database, create
            municipality = frappe.get_doc({
                'doctype': "Municipality",
                'bfsnr': element[field_index['bfsnr']] or "",
                'municipality': element[field_index['municipality']] or ""
            })
            municipality = municipality.insert()
            frappe.db.commit()
        else:
            # update pincode
            municipality = frappe.get_doc('Municipality', db_municipality[0]['name'])
            municipality.municipality = element[field_index['municipality']] or ""
            municipality.save()
            frappe.db.commit()
    
    return {'result': _('Successfully imported')}
