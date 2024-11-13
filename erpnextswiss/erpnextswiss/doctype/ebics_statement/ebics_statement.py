# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta, read_camt053
from frappe import _

class ebicsStatement(Document):
    def parse_content(self):
        if not self.xml_content:
            frappe.throw( _("Cannot parse this file: {0}. No content found.").format(self.name) )
            
        # read meta data
        meta = read_camt053_meta(self.xml_content)
        self.update({
            'currency': meta.get('currency'),
            'opening_balance': meta.get('opening_balance'),
            'closing_balance': meta.get('closing_balance')
        })
        account_matches = frappe.db.sql("""
            SELECT `name`
            FROM `tabAccount`
            WHERE `iban` = "{iban}" AND `account_type` = "Bank";
            """.format(iban=meta.get('iban')), as_dict=True)
        print("{0}".format(account_matches))
        if len(account_matches) > 0:
            self.account = account_matches[0]['name']
        
            # read transactions (only if account is available)
            transactions = read_camt053(self.xml_content, self.account)
            
            print("Txns: {0}".format(transactions))
            # read transactions into the child table
            for transaction in transactions.get('transactions'):
                print("{0}".format(transaction))
                # stringify lists to store them in child table
                if transaction.get("invoice_matches"):
                    transaction['invoice_matches'] = "{0}".format(transaction.get("invoice_matches"))
                if transaction.get("expense_matches"):
                    transaction['expense_matches'] = "{0}".format(transaction.get("expense_matches"))
                    
                self.append("transactions", transaction)
                
        else:
            frappe.log_error( _("Unable to find matching account: please check your accounts and set IBAN {0}").format(meta.get('iban')), _("ebics statement parsing failed") )
        
        # save
        self.save()
        frappe.db.commit()
        
        return
