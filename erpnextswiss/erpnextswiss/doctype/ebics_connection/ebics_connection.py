# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import os
import fintech
fintech.register()
from fintech.ebics import EbicsKeyRing, EbicsBank, EbicsUser, EbicsClient, BusinessTransactionFormat
#from fintech.sepa import Account, SEPACreditTransfer
from frappe import _
from frappe.utils.file_manager import save_file

class ebicsConnection(Document):
    def get_activation_wizard(self):
        # determine configuration stage
        if (not self.host_id) or (not self.url) or (not self.partner_id) or (not self.user_id) or (not self.key_password):
            stage = 0
        elif (not os.path.exists(self.get_keys_file_name())):
            stage = 1
        elif (not self.ini_sent):
            stage = 2
        elif (not self.hia_sent):
            stage = 3
        elif (not self.ini_letter_created):
            stage = 4
        elif (not self.hpb_downloaded):
            stage = 5
        elif (not self.activated):
            stage = 6
        else:
            stage = 7
            
        content = frappe.render_template(
            "erpnextswiss/erpnextswiss/doctype/ebics_connection/ebics_connection_wizard.html", 
            {
                'doc': self.as_dict(),
                'stage': stage
            }
        )
        return {'html': content, 'stage': stage}
        
        
    def get_keys_file_name(self):
        keys_file = "{0}.keys".format((self.name or "").replace(" ", "_"))
        full_keys_file_path = os.path.join(frappe.utils.get_bench_path(), "sites", frappe.utils.get_site_path()[2:], keys_file)
        return full_keys_file_path

    def get_client(self):
        keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=self.key_password)
        bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
        user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
        client = EbicsClient(bank, user)
        return client
        
    def create_keys(self):
        try:
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=self.key_password)
            bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            user.create_keys(keyversion='A006', bitlength=2048)
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

    def send_signature(self):
        try:
            client = self.get_client()
            client.INI()
            self.ini_sent = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
    
    def send_keys(self):
        try:
            client = self.get_client()
            client.HIA()
            self.hia_sent = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
    
    def create_ini_letter(self):
        try:
            # create ini letter
            file_name = "/tmp/ini_letter.pdf"
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=self.key_password)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            user.create_ini_letter(bankname=self.title, path=file_name)
            # load ini pdf
            f = open(file_name, "rb")
            pdf_content = r.read()
            f.close()
            # attach to ebics
            save_file("ini_letter.pdf", pdf_content, self.doctype, self.name, is_private=1)
            # remove tmp file
            os.remove(file_name)
            # mark created
            self.ini_letter_created = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
        
    def download_public_keys(self):
        try:
            client = self.get_client()
            client.HPB()
            self.hpb_downloaded = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
        
    def activate_account(self):
        try:
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=self.key_password)
            bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
            bank.activate_keys()
            self.activated = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

@frappe.whitelist()
def execute_payment(ebics_connection, payment_proposal):
    conn = frappe.get_doc("ebics Connection", ebics_connection)
    payment = frappe.get_doc("Payment Proposal", payment_proposal)
    
    # ebics v3.0 BTU/BTD
    CCT = BusinessTransactionFormat(
        service='SCT',
        msg_name='pain.001'
    )
    
    # generate content
    xml_transaction = payment.create_bank_file()['content']
    
    # upload data using v3.0 (H005)
    data = conn.BTD(CCT, xml_transaction)
    
    return
    
        
def get_transactions(ebics_connection, from_date, to_date):
    conn = frappe.get_doc("ebics Connection", ebics_connection)
    
    # ebics v3.0 BTU/BTD
    C53 = BusinessTransactionFormat(
        service='EOP',
        msg_name='camt.053'
    )
    
    # download data using v3.0 (H005)
    data = conn.BTD(C53, from_date, to_date)
    
    return
