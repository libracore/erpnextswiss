# -*- coding: utf-8 -*-
# Copyright (c) 2021-2023, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import urllib.request
import requests
import hmac
import hashlib
import base64
import json
from datetime import date, timedelta

API_BASE = "https://api.payrexx.com/v1.0/"

@frappe.whitelist()
def create_payment(title, description, reference, purpose, amount, 
    vat_rate, sku, currency, success_url):
    post_data = {
        "title": title,
        "description": description,
        "psp": 1,
        "referenceId": reference,
        "purpose": purpose,
        "amount": amount,
        "vatRate": vat_rate,
        "currency": currency,
        "sku": sku,
        "preAuthorization": 0,
        "reservation": 0,
        "successRedirectUrl": success_url
    }
    data = urllib.parse.urlencode(post_data).encode('utf-8')
    settings = frappe.get_doc("Payrexx Settings", "Payrexx Settings")
    if not settings.payrexx_api_key:
        frappe.throw( _("Please set payrexx API key in the Payrexx settings.") )
    dig = hmac.new(settings.payrexx_api_key.encode('utf-8'), msg=data, digestmod=hashlib.sha256).digest()
    post_data['ApiSignature'] = base64.b64encode(dig).decode()
    data = urllib.parse.urlencode(post_data, quote_via=urllib.parse.quote).encode('utf-8')
    r = requests.post("{0}Invoice/?instance={1}".format(API_BASE, settings.payrexx_instance), data=data)
    response = json.loads(r.content.decode('utf-8'))
    invoice = response['data'][0]
    return invoice

@frappe.whitelist()
def get_payment_status(payrexx_id):
    post_data = {}
    data = urllib.parse.urlencode(post_data).encode('utf-8')
    settings = frappe.get_doc("Payrexx Settings", "Payrexx Settings")
    if not settings.payrexx_api_key:
        frappe.throw( _("Please set payrexx API key in the Payrexx settings.") )
    dig = hmac.new(settings.payrexx_api_key.encode('utf-8'), msg=data, digestmod=hashlib.sha256).digest()
    post_data['ApiSignature'] = base64.b64encode(dig).decode()
    data = urllib.parse.urlencode(post_data, quote_via=urllib.parse.quote).encode('utf-8')
    r = requests.get("{0}Invoice/{2}/?instance={1}".format(API_BASE, settings.payrexx_instance, payrexx_id), data=data)
    response = json.loads(r.content.decode('utf-8'))
    invoice = response['data'][0]
    return invoice
