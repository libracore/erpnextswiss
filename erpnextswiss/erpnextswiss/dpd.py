# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
import requests
import json
import base64
from frappe.utils.file_manager import save_file

class DPD_API:
    def __init__(self):
        self.host = None
        self.delis_id = None
        self.password = None
        self.language = None
        self.token = None
        self.paper_format = "A6"
        self.sender_depot = None
        self.load_credentials()
        return
        
    def load_credentials(self):
        try:
            settings = frappe.get_doc("DPD Settings")
            self.host = (settings.host or "").rstrip("/")
            self.delis_id = settings.delis_id
            self.password = settings.get_password("password")
            self.lanugage = settings.language
            self.paper_format = settings.paper_format or "A6"
            self.sender_depot = settings.sender_depot
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
        if not frappe.db.exists("Shipment", shipment):
            frappe.throw("Invalid shipment: {0}".format(shipment))
        
        if not self.token:
            self.get_auth()
        
        shipment_doc = frappe.get_doc("Shipment", shipment)
        pickup_address = frappe.get_doc("Address", shipment_doc.pickup_address_name)
        delivery_address = frappe.get_doc("Address", shipment_doc.delivery_address_name)

        url = "{0}}/rest/services/ShipmentService/V3_2/storeOrders".format(self.host)

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
                            "product": "B2B",
                            "sender": {
                                "name1": shipment_doc.pickup_company,
                                "street": pickup_address.address_line1,
                                "country": frappe.get_value("Country", pickup_address.country, "code").upper(),
                                "zipCode": pickup_address.pincode,
                                "city": pickup_address.city
                            },
                            "recipient": {
                                "name1": shipment_doc.delivery_customer,
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

        response = requests.request("POST", url, headers=headers, data=payload)

        if response.status_code == requests.codes.ok:
            response_json = response.json()
            pdf_base64 = response_json.get("orderResult").get("parcellabelsPDF").get("authToken")
            mps_id = response_json.get("orderResult").get("shipmentResponses").get("identificationNumber")
            parcel_id = response_json.get("orderResult").get("shipmentResponses").get("parcelInformation").get("parcelLabelNumber")

            # update record
            shipment_doc.shipment_id = parcel_id
            shipment.save()
            frappe.db.commit()

            # attach pdf
            pdf = base64.b64decode(pdf_base64)
            file_name = "{0}.pdf".format(parcel_id)
            save_file(file_name, pdf, "Shipment", shipment, is_private=1)

        else:
            response.rasie_for_status()

        return
        
@frappe.whitelist()
def transmit_to_dpd(shipment):
    dpd = DPD_API()
    dpd.store_order(shipment)
    return
