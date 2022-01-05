# -*- coding: utf-8 -*-
# Copyright (c) 2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class VATquery(Document):
    def validate(self):
        forbidden_keywords = ["insert", "update", "delete"]
        for kw in forbidden_keywords:
            if kw in self.query.lower():
                frappe.throw( _("Only select queries are allowed") )
            

