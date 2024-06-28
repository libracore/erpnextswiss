# -*- coding: utf-8 -*-
# Copyright (c) 2022-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils.password import get_decrypted_password
from frappe.utils.data import get_url
import json

"""
Initiate a payment with Datatrans

Note: amount is in minor units, e.g. Cents. CHF 12.50 is therefore amount=1250
"""
def get_payment_link(currency, refno, amount, verify=True):
    settings = frappe.get_doc("Datatrans Settings", "Datatrans Settings")
    
    payload = {
        "currency": currency, 
        "refno": refno, 
        "amount": float(amount), 
        "paymentMethods": settings.get_payment_method_list(),
        "redirect": {
            "successUrl": settings.success_url or get_url(),
            "errorUrl": settings.error_url or get_url(),
            "cancelUrl": settings.cancel_url or get_url()
        }
    }

    auth = HTTPBasicAuth(settings.username, get_decrypted_password("Datatrans Settings", "Datatrans Settings", "password", False))
    
    r = requests.post("{0}/transactions".format(settings.endpoint), verify=verify, auth=auth, json=payload)
    
    transaction_id = None
    try:
        r_dict = json.loads(r.text)
        transaction_id = r_dict.get('transactionId')
    except:
        # something unexpected happened, but never mind, just return the empty transaction id
        transaction_id = None
        
    return {'success': 1, 'status': r.status_code, 'result': r.text, 'transaction_id': transaction_id}

"""
Get the status of a transaction
"""
def get_payment_status(transaction_id, verify=True):
    settings = frappe.get_doc("Datatrans Settings", "Datatrans Settings")
    
    auth = HTTPBasicAuth(settings.username, get_decrypted_password("Datatrans Settings", "Datatrans Settings", "password", False))
    
    r = requests.get("{0}/transactions/{1}".format(settings.endpoint, transaction_id), verify=verify, auth=auth)
    
    status = None
    try:
        status = json.loads(r.text)
    except:
        # something unexpected happened, but never mind, just return the empty status
        status = None
        
    return {'success': 1, 'status': r.status_code, 'result': r.text, 'status': status}
    
