# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import csv
from frappe.utils.background_jobs import enqueue

class Pincode(Document):
	pass

def import_pincodes_from_file(filename):
    f = open(filename, "r")
    import_pincodes(f.read())

@frappe.whitelist()
def enqueue_import_pincodes(content):
    kwargs={
          'content': content
        }
    
    enqueue("erpnextswiss.erpnextswiss.doctype.pincode.pincode.import_pincodes",
        queue='long',
        timeout=15000,
        **kwargs)
    return {'result': _('Import started...')}

def import_pincodes(content):   
    isfirst = True
    field_index = {}
    # read csv
    elements = unicode_csv_reader(content.splitlines())
    # process elements
    for element in elements:
        if isfirst:
            isfirst = False;
            # loop through cells
            for i in range(0, len(element)):
                field_index[element[i].lower()] = i
            continue
        # check if the pincode is already in the database
        db_pincodes = frappe.get_all("Pincode", 
            filters={'pincode': element[field_index['pincode']], 'city': element[field_index['city']]}, 
            fields=['name'])
        if not db_pincodes:
            # pincode is not in the database, create
            try:
                country_code = element[field_index['country_code']].lower()
            except:
                country_code = "ch"
            db_country = frappe.get_all("Country", 
                filters={'code': country_code}, 
                fields=['name'])
            if db_country:
                country = db_country[0]['name']
            else:
                country = "Switzerland"
            pincode = frappe.get_doc({
                'doctype': "Pincode",
                'pincode': element[field_index['pincode']] or 0,
                'city': element[field_index['city']] or "",
                'canton': element[field_index['canton']] or "",
                'canton_code': element[field_index['canton_code']] or "",
                'country': country,
                'country_code': country_code,
                'title': "{0}-{1}".format(element[field_index['pincode']] or 0, element[field_index['city']] or "")
            })
            pincode = pincode.insert()
            frappe.db.commit()
    
    return {'result': _('Successfully imported')}

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')
