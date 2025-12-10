# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
import requests
import json

class DPD_API:
    def __init__(self):
        self.host = None
        self.delis_id = None
        self.password = None
        self.language = None
        self.token = None
        self.load_credentials()
        return
        
    def load_credentials(self):
        try:
            settings = frappe.get_doc("DPD Settings")
            self.host = (settings.host or "").rstrip("/")
            self.delis_id = settings.delis_id
            self.password = settings.get_password("password")
            self.lanugage = settings.language
        except Exception as e:
            frappe.throw("Unable to find DPD settings: {0}".format(e))
        return
        
    def get_auth(self):
        url = "{0}/rest/services/LoginService/V2_1/getAuth".format(self.host)

        payload = json.dumps({
          "delisId": self.delis_id,
          "password": self.password,
          "messageLanguage": self.language
        })
        headers = {
          'Content-Type': 'application/json'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)

        if response.status_code == requests.codes.ok:
            self.token = response.json().get("getAuthResponse").get("return").get("authToken")
        else:
            response.raise_for_status()
        
        return
        
    def store_order(self, shipment):
        return
        
