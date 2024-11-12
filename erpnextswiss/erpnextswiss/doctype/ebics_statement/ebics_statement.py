# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta

class ebicsStatement(Document):
    def parse_content(self):
        meta = read_camt053_meta(self.xml_content)
        self.update({
            'currency': meta.get('currency'),
            'opening_balance': meta.get('opening_balance'),
            'closing_balance': meta.get('closing_balance')
        })
        account_matches = frappe.db.sql("""
            SELECT `name`
            FROM `tabAccount`
            WHERE `iban` = "{iban}";
            """.format(iban=meta.get('iban')), as_dict=True)
            
        if len(account_matches) > 0:
            self.account = account_matches[0]['name']
        
        self.save()
        frappe.db.commit()
        
        return
