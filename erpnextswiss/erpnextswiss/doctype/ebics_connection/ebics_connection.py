# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#

import frappe
from frappe.model.document import Document
import os
import fintech
fintech.register()
from fintech.ebics import EbicsKeyRing, EbicsBank, EbicsUser, EbicsClient, BusinessTransactionFormat
#from fintech.sepa import Account, SEPACreditTransfer
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.password import get_decrypted_password
from datetime import datetime

class ebicsConnection(Document):
    def before_save(self):
        # make sure synced_until is in date format
        if self.synced_until and not type(self.synced_until) == datetime.date:
            if type(self.synced_until) == str:
                self.synced_until = datetime.strptime(self.synced_until, "%Y-%m-%d").date()
            elif type(self.synced_until) == datetime.datetime:
                self.synced_until =self.synced_until.date()
                
        return
        
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
        passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
        keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
        bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
        user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
        client = EbicsClient(bank, user, version=self.ebics_version)
        return client
        
    def create_keys(self):
        try:
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            user.create_keys(keyversion='A006', bitlength=2048)
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

    def create_certificate(self):
        try:
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            x509_dn = {
                'commonName': '{0} ebics'.format(self.company or "libracore ERP"),
                'organizationName': (self.company or "libracore ERP"),
                'organizationalUnitName': 'Administration',
                'countryName': 'CH',
                'stateOrProvinceName': 'ZH',
                'localityName': 'Winterthur',
                'emailAddress': 'info@libracore.com'
            }
            user.create_certificates(validity_period=5, **x509_dn)
            
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
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
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
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
            bank.activate_keys()
            self.activated = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

    @frappe.whitelist()
    def execute_payment(self, payment_proposal):
        payment = frappe.get_doc("Payment Proposal", payment_proposal)
        
        # ebics v3.0 BTU/BTD
        CCT = BusinessTransactionFormat(
            service='MCT',
            msg_name='pain.001',
            scope='CH'
        )
        
        # generate content
        xml_transaction = payment.create_bank_file()['content']
        
        # upload data using v3.0 (H005)
        client = self.get_client()
        data = client.BTD(CCT, xml_transaction)
        
        return
        
            
    def get_transactions(self, date, debug=False):
        if type(date) == date or type(date) == datetime:
            date = date.strftime("%Y-%m-%d")

        try:
            client = self.get_client()
            if self.ebics_version == "H005":
                # ebics v3.0 BTU/BTD
                C53 = BusinessTransactionFormat(
                    service='EOP',
                    msg_name='camt.053',
                    scope='CH',
                    container='ZIP'
                )

                # download data using v3.0 (H005)
                data = client.BTD(C53, date, date)
            else:
                # use version 2.5
                data = client.Z53(
                    start=date,                     # should be in YYYY-MM-DD
                    end=date,
                )
            client.confirm_download()
            
            # check data
            if len(data) > 0:
                # there should be one node for each account for this day
                for account, content in data.items():
                    stmt = frappe.get_doc({
                        'doctype': 'ebics Statement',
                        'ebics_connection': self.name,
                        'file_name': account,
                        'xml_content': content,
                        'date': date,
                        'company': self.company
                    })
                    stmt.insert()
                    if debug:
                        print("Inserted {0}".format(account))
                    frappe.db.commit()
                    # process data
                    if debug:
                        print("Parsing data...")
                    stmt.parse_content()
                    
                    # if there are no transactions: drop file
                    if len(stmt.transactions) == 0:
                        stmt.delete()
                        continue
                        
                    if debug:
                        print("Processing transactions...")
                    stmt.process_transactions()
                
                # update sync date
                if not self.synced_until or self.synced_until < datetime.strptime(date, "%Y-%m-%d").date():
                    self.synced_until = date
                    self.save()
                    frappe.db.commit()
                    
        except fintech.ebics.EbicsFunctionalError as err:
            if "{0}".format(err) == "EBICS_NO_DOWNLOAD_DATA_AVAILABLE":
                # this is not a problem, simply no data
                pass
            else:
                frappe.log_error("{0}".format(err), _("ebics Interface Error") )
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
