# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.edi import create_pricat
from frappe import _

class EDIConnection(Document):
    def validate(self):
        if self.transmission_mode == "Email" and not self.email_recipient:
            frappe.throw( _("Please define a target email address for transmission mode Email"), _("Validation") )
        return
    
    def create_file(self):
        if self.edi_type == "PRICAT":
            create_pricat(self.name)
        return
        
