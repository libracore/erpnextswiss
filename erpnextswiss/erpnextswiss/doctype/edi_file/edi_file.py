# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.edi import download_pricat, download_desadv, get_gtin
from erpnextswiss.erpnextswiss.attach_pdf import create_folder
from frappe.utils import cint
from frappe.utils.file_manager import save_file
from frappe.email.queue import send

class EDIFile(Document):
    def on_submit(self):
        # create and transmit file
        self.transmit_file()
        
        return
        
    def download_file(self):
        content = None
        if self.edi_type == "PRICAT":
            content = download_pricat(self.name)
        if self.edi_type == "DESADV":
            content = download_desadv(self.name)
        return { 'content': content }
        
    def get_item_details(self, item_code):
        item = frappe.get_doc("Item", item_code)
        price_list = frappe.get_value("EDI Connection", self.edi_connection, "price_list")
        retail_price_list = frappe.get_value("EDI Connection", self.edi_connection, "retail_price_list")
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
        # get retail price
        retail_rates = frappe.db.sql("""
            SELECT 
                `tabItem Price`.`price_list_rate` AS `rate`
            FROM `tabItem Price`
            WHERE 
                `tabItem Price`.`price_list` = "{price_list}"
                AND `tabItem Price`.`item_code` = "{item_code}"
                AND (`tabItem Price`.`valid_from` IS NULL OR `tabItem Price`.`valid_from` <= CURDATE())
                AND (`tabItem Price`.`valid_upto` IS NULL OR `tabItem Price`.`valid_upto` >= CURDATE())
            ORDER BY `tabItem Price`.`valid_from` DESC;
            """.format(item_code=item_code, price_list=retail_price_list), as_dict=True)
        tax_factor = 1
        if self.taxes:
            for t in self.taxes:
                tax_factor += t.rate / 100
        if len(retail_rates) > 0:
            details['retail_rate'] = round(tax_factor * retail_rates[0]['rate'], 2)
        else:
            details['retail_rate'] = 0
        # get GTIN
        details['gtin'] = get_gtin(item)
                
        return details

    """
    Create and attach the file
    """
    def transmit_file(self):
        if frappe.get_value("EDI Connection", self.edi_connection, "transmission_mode") == "Email":
            content = self.download_file()
            # check if file was created
            if 'content' in content:
                # create EDI file attachment folder
                folder = create_folder("edi_file", "Home")
                # store EDI File
                f = save_file(
                    "{0}.edi".format(self.name), 
                    content['content'], 
                    "EDI File", 
                    self.name, 
                    folder=folder, 
                    is_private=True
                )
                # send mail
                send(
                    recipients=frappe.get_value("EDI Connection", self.edi_connection, "email_recipient"), 
                    subject=self.name, 
                    message=self.name, 
                    reference_doctype="EDI File", 
                    reference_name=self.name,
                    attachments=[{'fid': f.name}]
                )
                
            else:
                frappe.log_error("No content found: {0}".format(self.name), "Transmit EDI File")
        return
