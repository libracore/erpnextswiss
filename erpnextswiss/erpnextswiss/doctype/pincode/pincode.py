# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import csv
from frappe.utils.background_jobs import enqueue
from math import sin, cos, sqrt, atan2, radians

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
    elements = csv.reader(content.splitlines(), dialect=csv.excel)
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
                'bfsnr': element[field_index['bfsnr']] or "",
                'country': country,
                'country_code': country_code,
                'title': "{0}-{1}".format(element[field_index['pincode']] or 0, element[field_index['city']] or ""),
                'longitude': element[field_index['longitude']] or "",
                'latitude': element[field_index['latitude']] or "",
            })
            pincode = pincode.insert()
            frappe.db.commit()
        else:
            # update pincode
            pincode = frappe.get_doc('Pincode', db_pincodes[0]['name'])
            pincode.longitude = element[field_index['longitude']] or ""
            pincode.latitude = element[field_index['latitude']] or ""
            pincode.bfsnr = element[field_index['bfsnr']] or ""
            pincode.save()
            frappe.db.commit()
    
    return {'result': _('Successfully imported')}

@frappe.whitelist()
def get_distance(pincode1, pincode2):
    # compute the distance between to pincodes
    # approximate radius of earth in km
    R = 6373.0

    p1 = frappe.get_all("Pincode", filters={'pincode': pincode1}, fields=['name', 'longitude', 'latitude'])
    p2 = frappe.get_all("Pincode", filters={'pincode': pincode2}, fields=['name', 'longitude', 'latitude'])

    if p1 and p2:
        if p2[0]['longitude'] and p1[0]['longitude'] and p2[0]['latitude'] and p1[0]['latitude']:
            lat1 = radians(float(p1[0]['latitude']))
            lat2 = radians(float(p2[0]['latitude']))
            long1 = radians(float(p1[0]['longitude']))
            long2 = radians(float(p2[0]['longitude']))
            print("{0}/{1} .. {2}/{3}".format(lat1, long1, lat2, long2))
            dlon = long2 - long1
            dlat = lat2 - lat1

            a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))

            distance = R * c

            return round(distance, 2)
        else:
            print("lat/long missing")
            return 0.0
    else:
        print("pincode not found")
        return 0.0
