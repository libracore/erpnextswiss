# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
import requests
from requests.auth import HTTPBasicAuth
from frappe.utils.password import get_decrypted_password
from frappe.utils.data import get_url

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
    
    return {'success': 1, 'status': r.status_code, 'result': r.text}
