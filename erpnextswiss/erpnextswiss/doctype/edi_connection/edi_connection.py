# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.edi import create_pricat

class EDIConnection(Document):
    def create_file(self):
        if self.edi_type == "PRICAT":
            create_pricat(self.name)
        return
        