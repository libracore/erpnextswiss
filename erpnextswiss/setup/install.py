# -*- coding: utf-8 -*-
# License: AGPL v3. See LICENCE

import frappe

def after_install():
    install_basic_docs()
    frappe.db.commit()
    

def install_basic_docs():
    install_bankimport_banks = [
        {'doctype': 'BankImport Bank','bank_name': 'UBS','legacy_ref': 'ubs','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1},
        {'doctype': 'BankImport Bank','bank_name': 'ZKB','legacy_ref': 'zkb','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1},
        {'doctype': 'BankImport Bank','bank_name': 'Raiffeisen','legacy_ref': 'raiffeisen','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1},
        {'doctype': 'BankImport Bank','bank_name': 'CreditSwiss','legacy_ref': 'cs','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1},
        {'doctype': 'BankImport Bank','bank_name': 'Migrosbank','legacy_ref': 'migrosbank','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1},
        {'doctype': 'BankImport Bank','bank_name': 'Postfinance','legacy_ref': 'postfinance','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1}
    ]
    
    doc = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
    for d in install_bankimport_banks:
        doc.append("bankimport_table",d)
    doc.save()
    
