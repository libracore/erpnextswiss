# -*- coding: utf-8 -*-
# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DatatransSettings(Document):
    def get_payment_method_list(self):
        payment_methods = []
        for p in self.payment_methods:
            payment_methods.append(p.code)
        return payment_methods

