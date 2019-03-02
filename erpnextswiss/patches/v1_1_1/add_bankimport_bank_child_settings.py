import frappe
from frappe import _

def execute():
    frappe.reload_doc("erpnextswiss", "doctype", "bankimport_bank")
    frappe.reload_doc("erpnextswiss", "doctype", "erpnextswiss_settings")
    frappe.msgprint("Test")
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
            if not frappe.db.exists(d["doctype"], d["bank_name"]):
                doc.append("bankimport_table",d)
    doc.save()
    