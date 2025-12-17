# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
import requests
import json
import base64
from frappe.utils.file_manager import save_file
from frappe.utils import cint

class DPD_API:
    def __init__(self):
        self.host = None
        self.delis_id = None
        self.password = None
        self.language = None
        self.token = None
        self.paper_format = "A6"
        self.product = "B2C"
        self.sender_depot = None
        self.debug = False
        self.enabled = False
        self.load_credentials()
        return
        
    def load_credentials(self):
        try:
            settings = frappe.get_doc("DPD Settings")
            self.host = (settings.host or "").rstrip("/")
            self.delis_id = settings.delis_id
            self.password = settings.get_password("password")
            self.language = settings.language
            self.paper_format = settings.paper_format or "A6"
            self.product = settings.product or "B2C"
            self.sender_depot = settings.sender_depot
            self.debug = cint(settings.debug)
            self.enabled = cint(settings.enabled)
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
        
        if self.debug:
            frappe.log_error("{0}\n\n{1}".format(headers, payload), "DPD Shipment Auth (Debug)")
        response = requests.request("POST", url, headers=headers, data=payload)

        if self.debug:
            frappe.log_error("{0}".format(response.text), "DPD Shipment Auth Response (Debug)")
            
        if response.status_code == requests.codes.ok:
            self.token = response.json().get("getAuthResponse").get("return").get("authToken")
        else:
            response.raise_for_status()
        
        return
    
    def store_order(self, shipment):
        if not self.enabled:
            frappe.log_error("DPD is disabled in DPD settings", "DPD Shipment request")
            
        if not frappe.db.exists("Shipment", shipment):
            frappe.throw("Invalid shipment: {0}".format(shipment))
        
        if not self.token:
            self.get_auth()
        
        parcel_id = None
        shipment_doc = frappe.get_doc("Shipment", shipment)
        pickup_address = frappe.get_doc("Address", shipment_doc.pickup_address_name)
        delivery_address = frappe.get_doc("Address", shipment_doc.delivery_address_name)

        url = "{0}/rest/services/ShipmentService/V3_2/storeOrders".format(self.host)

        parcels = []
        for p in shipment_doc.shipment_parcel:
            parcels.append({
                'volume': "{l:03d}{w:03d}{h:03d}".format(l=p.length, w=p.width, h=p.height),
                'weight': cint(p.weight * 100)                          # int in 10 gram units
            })
        
        # use recipient name from shipment if available, otherwise, fall back to customer name
        recipient_name = shipment_doc.get("recipient_name") \
            or frappe.get_value("Customer", shipment_doc.delivery_customer, "customer_name") if frappe.db.exists("Customer", shipment_doc.delivery_customer) else shipment_doc.delivery_customer
        product = shipment_doc.get("product") or self.product           # use product from shipment if avalable or fallback from settings
        
        payload = json.dumps({
            "authentication": {
                "delisId": self.delis_id,
                "authToken": self.token,
                "messageLanguage": self.language
            },
            "storeOrders": {
                "printOptions": {
                    "printerLanguage": "PDF",
                    "paperFormat": self.paper_format
                },
                "order": [
                    {
                        "generalShipmentData": {
                            "sendingDepot": self.sender_depot,
                            "product": product,
                            "sender": {
                                "name1": shipment_doc.pickup_company,
                                "street": pickup_address.address_line1,
                                "country": frappe.get_value("Country", pickup_address.country, "code").upper(),
                                "zipCode": pickup_address.pincode,
                                "city": pickup_address.city
                            },
                            "recipient": {
                                "name1": recipient_name,
                                "street": delivery_address.address_line1,
                                "country": frappe.get_value("Country", delivery_address.country, "code").upper(),
                                "zipCode": delivery_address.pincode,
                                "city": delivery_address.city
                            }
                        },
                        "parcels": [
                            {}
                        ],
                        "productAndServiceData": {
                            "orderType": "consignment"
                        }
                    }
                ]
            }
        })
        headers = {
            'Content-Type': 'application/json'
        }

        if self.debug:
            frappe.log_error("{0}\n\n{1}".format(headers, payload), "DPD Shipment (Debug)")
        response = requests.request("POST", url, headers=headers, data=payload)

        if self.debug:
            frappe.log_error("{0}".format(response.text), "DPD Shipment Response (Debug)")
            
        if response.status_code == requests.codes.ok:
            response_json = response.json()
            pdf_base64 = response_json.get("orderResult").get("parcellabelsPDF")
            mps_id = response_json.get("orderResult").get("shipmentResponses")[0].get("identificationNumber")
            parcel_id = response_json.get("orderResult").get("shipmentResponses")[0].get("parcelInformation")[0].get("parcelLabelNumber")

            # attach pdf
            pdf = base64.b64decode(pdf_base64)
            file_name = "{0}.pdf".format(parcel_id)
            save_file(file_name, pdf, "Shipment", shipment, is_private=1)

        else:
            response.raise_for_status()

        return parcel_id
        
@frappe.whitelist()
def transmit_to_dpd(shipment):
    dpd = DPD_API()
    parcel_id = dpd.store_order(shipment)
    return parcel_id
