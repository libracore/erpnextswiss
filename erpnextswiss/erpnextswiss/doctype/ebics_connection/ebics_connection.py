# -*- coding: utf-8 -*-
# Copyright (c) 2024-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#

import frappe
from frappe.model.document import Document
import os
try:
    import fintech
    fintech.register()
    from fintech.ebics import EbicsKeyRing, EbicsBank, EbicsUser, EbicsClient, BusinessTransactionFormat
    #from fintech.sepa import Account, SEPACreditTransfer
except:
    pass            # failed to load fintech, skip
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.password import get_decrypted_password
from frappe.utils import cint
from datetime import date, datetime
from xml.etree import ElementTree


def _xml_name(element):
    return element.tag.rsplit('}', 1)[-1]


def _xml_child(element, name):
    return next((child for child in element if _xml_name(child) == name), None)


def _xml_text(element, name):
    child = _xml_child(element, name) if element is not None else None
    return (child.text or '').strip() if child is not None else ''


def _matches_payment_service(service, payment_btf):
    if service is None or _xml_text(service, 'ServiceName') != payment_btf['service']:
        return False
    if _xml_text(service, 'Scope') != payment_btf['scope']:
        return False
    message = _xml_child(service, 'MsgName')
    if message is None or (message.text or '').strip() != payment_btf['msg_name']:
        return False
    return not payment_btf.get('version') or message.get('version') == payment_btf['version']


def _has_transport_permission(htd, debtor_iban, payment_btf, min_signatures=1):
    """Trust only account-specific T and the bank's required signature quorum."""
    root = ElementTree.fromstring(htd)
    partner = _xml_child(root, 'PartnerInfo')
    user = _xml_child(root, 'UserInfo')
    if partner is None or user is None:
        return False

    account_ids = set()
    for account in partner:
        if _xml_name(account) != 'AccountInfo':
            continue
        account_number = _xml_text(account, 'AccountNumber')
        if ''.join(account_number.split()).upper() == debtor_iban:
            account_ids.add(account.get('ID'))
    if not account_ids:
        return False

    # HTD OrderInfo gives the bank's minimum signature count for this BTF.
    # Missing or conflicting order information is not evidence of a safe VEU.
    signature_counts = []
    for order in partner:
        if _xml_name(order) != 'OrderInfo' or _xml_text(order, 'AdminOrderType') != 'BTU':
            continue
        if _matches_payment_service(_xml_child(order, 'Service'), payment_btf):
            try:
                signature_counts.append(int(_xml_text(order, 'NumSigRequired')))
            except ValueError:
                return False
    if not signature_counts or min(signature_counts) < min_signatures:
        return False

    levels = set()
    for permission in user:
        if _xml_name(permission) != 'Permission':
            continue
        if _xml_text(permission, 'AdminOrderType') != 'BTU':
            continue
        if not _matches_payment_service(_xml_child(permission, 'Service'), payment_btf):
            continue
        if _xml_text(permission, 'AccountID') in account_ids:
            levels.add(permission.get('AuthorisationLevel'))
    return levels == {'T'}

class ebicsConnection(Document):
    def before_save(self):
        # make sure synced_until is in date format
        if isinstance(self.synced_until, datetime):
            self.synced_until = self.synced_until.date()
        elif isinstance(self.synced_until, str) and self.synced_until:
            self.synced_until = datetime.strptime(self.synced_until, "%Y-%m-%d").date()
        elif self.synced_until and not isinstance(self.synced_until, date):
            raise TypeError("synced_until must be a date or an ISO date string")
                
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
        site_path = frappe.utils.get_site_path()
        if not os.path.isabs(site_path):
            site_path = os.path.join(
                frappe.utils.get_bench_path(),
                "sites",
                site_path.removeprefix("./")
            )
        return os.path.join(site_path, keys_file)

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
            if self.ebics_version == "H005":              # H005 requires certificates: create them
                self.create_certificate()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

    def create_certificate(self):
        try:
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            company = frappe.get_doc("Company", self.company)
            address_name = frappe.db.sql("""
                SELECT a.name
                FROM `tabAddress` a
                INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name
                WHERE dl.parenttype = 'Address'
                  AND dl.link_doctype = 'Company'
                  AND dl.link_name = %s
                  AND a.disabled = 0
                ORDER BY a.is_primary_address DESC, a.modified DESC
                LIMIT 1
            """, self.company)
            address = frappe.get_doc("Address", address_name[0][0]) if address_name else None
            x509_dn = {
                'commonName': '{0} EBICS'.format(company.company_name),
                'organizationName': company.company_name,
                'organizationalUnitName': 'Buchhaltung',
                'countryName': (self.get('scope') or 'CH'),
                'localityName': (address.city if address else company.company_name),
                'emailAddress': (company.email or frappe.session.user)
            }
            if address and address.state:
                x509_dn['stateOrProvinceName'] = address.state
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
            pdf_content = f.read()
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

    @frappe.whitelist(methods=["POST"])
    def execute_payment(self, payment_proposal):
        self.check_permission("write")
        payment = frappe.get_doc("Payment Proposal", payment_proposal)
        payment.check_permission("write")
        
        # ebics v3.0 BTU/BTD
        payment_btf = {
            'service': 'MCT',
            'msg_name': 'pain.001',
            'scope': (self.get('scope') or 'CH')
        }
        if self.get('payment_btf_version'):
            payment_btf['version'] = self.get('payment_btf_version')
        CCT = BusinessTransactionFormat(**payment_btf)
        
        # generate content
        bank_file = payment.create_bank_file()
        xml_transaction = bank_file['content']
        
        # upload data using v3.0 (H005)
        client = self.get_client()
        if not cint(self.get('require_veu')):
            client.BTU(CCT, xml_transaction)
            return {'status': 'transmitted'}

        if payment.docstatus != 1 or payment.company != self.company:
            frappe.throw(_("Only submitted proposals for this EBICS connection's company may be sent."))
        account = frappe.get_doc('Account', payment.pay_from_account)
        debtor_iban = ''.join((account.iban or '').split()).upper()
        if not debtor_iban or account.company != self.company:
            frappe.throw(_("The debit account has no valid IBAN for this company."))
        try:
            transport_only = _has_transport_permission(
                client.HTD(), debtor_iban, payment_btf,
                min_signatures=max(1, cint(self.get('veu_signatures_required'))),
            )
        except (ElementTree.ParseError, TypeError, ValueError):
            transport_only = False
        if not transport_only:
            frappe.throw(_("EBICS payment blocked: the bank has not confirmed a T (transport-only) permission and the configured VEU signature quorum for this debit account and payment format. Ask the bank to enable VEU; an E signature could execute the payment immediately."))

        # Persist the attempt before contacting the bank. On a timeout or crash, an
        # operator must reconcile the order instead of accidentally submitting twice.
        locked = frappe.db.sql(
            "SELECT ebics_transfer_status FROM `tabPayment Proposal` WHERE name = %s FOR UPDATE",
            payment.name,
        )
        if not locked or locked[0][0]:
            frappe.throw(_("This payment proposal has already been sent or attempted via EBICS. Check the bank status before any new submission."))
        frappe.db.set_value('Payment Proposal', payment.name, {
            'ebics_transfer_status': 'Sending',
            'ebics_transfer_message_id': bank_file.get('message_id'),
        }, update_modified=False)
        frappe.db.commit()
        try:
            order_id = client.BTU(CCT, xml_transaction)
        except Exception:
            frappe.db.set_value('Payment Proposal', payment.name,
                                'ebics_transfer_status', 'Transmission uncertain', update_modified=False)
            frappe.db.commit()
            raise
        order_id = order_id if isinstance(order_id, str) else ''
        frappe.db.set_value('Payment Proposal', payment.name, {
            'ebics_transfer_status': 'Awaiting bank VEU',
            'ebics_transfer_order_id': order_id,
        }, update_modified=False)
        frappe.db.commit()
        return {'status': 'awaiting_bank_veu', 'order_id': order_id,
                'message_id': bank_file.get('message_id')}
        
            
    def get_transactions(self, date=None, debug=False):
        if self.ebics_version == "H005":
            # H005 EOP is a current-pending bank delivery, not a date search.
            # Route it through the durable receipt/acknowledgement workflow.
            if date is not None:
                raise ValueError("H005 historical date retrieval is not supported; use current pending EBICS sync")
            from erpnextswiss.erpnextswiss.ebics_automation import sync_connection
            return sync_connection(self.name, debug=debug)
        if date is None:
            raise ValueError("A date is required for legacy H004 statement retrieval")
        if hasattr(date, "strftime"):
            date = date.strftime("%Y-%m-%d")

        try:
            client = self.get_client()
            # The historical H004 path is separate from current H005 delivery.
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


@frappe.whitelist(methods=["POST"])
def execute_payment(ebics_connection, payment_proposal):
    connection = frappe.get_doc("ebics Connection", ebics_connection)
    connection.check_permission("write")
    return connection.execute_payment(payment_proposal)
