# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.edi import download_pricat
from frappe.utils import cint

class EDIFile(Document):
    def download_file(self):
        content = download_pricat(self.name)
        return { 'content': content }
        
    def get_item_details(self, item_code):
        item = frappe.get_doc("Item", item_code)
        price_list = frappe.get_value("EDI Connection", self.edi_connection, "price_list")
        details = {
            'item_code': item_code,
            'item_name': item.item_name,
            'attributes': item.attributes
        }
        # check action
        previous_occurrences = frappe.db.sql("""
            SELECT 
                `tabEDI File Pricat Item`.`item_code`,
                `tabEDI File Pricat Item`.`action`
            FROM `tabEDI File Pricat Item`
            LEFT JOIN `tabEDI File` ON `tabEDI File`.`name` = `tabEDI File Pricat Item`.`parent`
            WHERE 
                `tabEDI File Pricat Item`.`item_code` = "{item_code}"
                AND `tabEDI File`.`edi_connection` = "{edi_connection}"
            ORDER BY `tabEDI File`.`modified` DESC;
            """.format(item_code=item_code, edi_connection=self.edi_connection), as_dict=True)
        if len(previous_occurrences) > 0:
            # this item has occurred
            if cint(item.disabled) == 1:
                details['action'] = "2=Delete"
            else:
                details['action'] = "3=Change"
        else:
            details['action'] = "1=Add"
        # get price
        rates = frappe.db.sql("""
            SELECT 
                `tabItem Price`.`price_list_rate` AS `rate`
            FROM `tabItem Price`
            WHERE 
                `tabItem Price`.`price_list` = "{price_list}"
                AND `tabItem Price`.`item_code` = "{item_code}"
                AND (`tabItem Price`.`valid_from` IS NULL OR `tabItem Price`.`valid_from` <= CURDATE())
                AND (`tabItem Price`.`valid_upto` IS NULL OR `tabItem Price`.`valid_upto` >= CURDATE())
            ORDER BY `tabItem Price`.`valid_from` DESC;
            """.format(item_code=item_code, price_list=price_list), as_dict=True)
        if len(rates) > 0:
            details['rate'] = rates[0]['rate']
        else:
            details['rate'] = 0
        # get GTIN
        for barcode in item.barcodes:
            if barcode.barcode_type == "EAN":
                details['gtin'] = barcode.barcode
                
        return details
