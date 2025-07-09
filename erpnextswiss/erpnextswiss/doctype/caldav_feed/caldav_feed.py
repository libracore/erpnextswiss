# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe import _

class CalDavFeed(Document):
    def before_save(self):
        # in case crm feed is enabled, make sure there is a secret
        if cint(self.crm_feed_enabled):
            if not self.crm_secret:
                self.crm_secret = frappe.generate_hash(self.doctype, 20)
                
            if not self.crm_source_field:
                self.crm_source_field = "contact_date" if self.crm_source == "Lead" else "follow_up"
                
            # check if source field is available
            source_meta = frappe.get_meta(self.crm_source)
            has_target = False
            for f in source_meta.fields:
                if f.fieldname == self.crm_source_field:
                    has_target = True
                    break
            if not has_target:
                frappe.throw( _("Invalid source field. Please use an existing field of {0}.").format(self.crm_source))
                
        if cint(self.todo_feed_enabled):
            if not self.todo_secret:
                self.todo_secret = frappe.generate_hash(self.doctype, 20)
        
        return
        
