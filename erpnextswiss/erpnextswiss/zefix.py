# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore AG and contributors
# For license information, please see license.txt
# Interface to the ZEFIX platform

import requests
from requests.auth import HTTPBasicAuth
from frappe.utils.password import get_decrypted_password
import frappe
import json
from frappe.utils import cint

ENDPOINTS = {
    'test': 'https://www.zefixintg.admin.ch/ZefixPublicREST/',
    'prod': 'https://www.zefix.admin.ch/ZefixPublicREST/'
}

"""
Find a company by its name

Returns a structure like
[
    {
        "name": "Company",
        "uid": "CHE123456789",
        "status": "ACTIVE"
    }
]
"""
@frappe.whitelist()
def find_company(company_name, debug=False, active_only="true"):
    url = get_endpoint('find_company', debug)
    payload = {
        "activeOnly": active_only,
        "name": company_name
    }
    headers = {"Content-type": "application/json", "Accept": "*/*"}
    r = requests.post(url, data=json.dumps(payload), auth=get_auth(), headers=headers)
    if r.status_code != 200:
        frappe.log_error("Error reading company: {0}: {1}".format(r.status_code, r.content), "Zefix find company")
        print("{0}".format(r.content))
        return {'error': r.status_code}
    else:
        data = json.loads(r.text)
        if debug:
            print("{0}".format(data))
        return data

"""
Find a company by its UID

Returns a structure like
[
    {
        "name": "Company", 
        "uid": "CHE123456789",
        "status": "ACTIVE",
        "address": {
            "organisation": "Company",
            "street": "Street",
            "houseNumber": "15",
            "swissZipCode": "8400",
            "city": "Winterthur"
        }
    }
]
"""
@frappe.whitelist()
def get_company(uid, debug=False):
    url = get_endpoint('get_company', debug) + "/" + uid
    r = requests.get(url, auth=get_auth())
    if r.status_code != 200:
        frappe.log_error("Error getting company: {0}".format(r.content), "Zefix get company")
        print("{0}".format(r.content))
        return {'error': r.status_code}
    else:
        data = json.loads(r.text)
        if debug:
            print("{0}".format(r))
        return data

def get_endpoint(target, debug=False):
    # collect base url
    if debug:
        url = ENDPOINTS['test']
    else:
        url = ENDPOINTS['prod']
    # define endpoints here
    if target == 'find_company':
        url += "api/v1/company/search"
    elif target == 'get_company':
        url += "api/v1/company/uid"
    # return full url endpoint
    return url
    
def get_auth():
    user = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'zefix_user')
    pw = frappe.utils.password.get_decrypted_password("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'zefix_pw')
    auth = HTTPBasicAuth(user, pw)
    return auth

"""
Get a Tax ID (and name) from a company name (e.g. customer, supplier)
"""
@frappe.whitelist()
def get_party_tax_id(party_name):
    if cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'enable_zefix')) == 1:
        company_matches = find_company(party_name)
        if company_matches and isinstance(company_matches, list) and len(company_matches) == 1:
            return {'name': company_matches[0]['name'], 'uid': company_matches[0]['uid']}
    return None

"""
Find an address from a link (e.g. on address references)
"""
@frappe.whitelist()
def get_address_from_link(dt, dn):
    doc = frappe.get_doc(dt, dn)
    if doc.tax_id:
        company_matches = get_company(uid=doc.tax_id)
        if company_matches and isinstance(company_matches, list) and len(company_matches) == 1:
            return {
                'street': "{0} {1}".format((company_matches[0]['address']['street'] or ""), 
                    (company_matches[0]['address']['houseNumber'] or "")), 
                'city': company_matches[0]['address']['city'],
                'pincode': company_matches[0]['address']['swissZipCode'],
                'canton': company_matches[0]['canton']
            } 
    return None
        
"""
Check if Zefix is enabled
"""
@frappe.whitelist()
def is_zefix_enabled():
    return cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'enable_zefix'))
