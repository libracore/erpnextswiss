# -*- coding: utf-8 -*-
# Copyright (c) 2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import os
from erpnextswiss.erpnextswiss.zugferd.zugferd import import_pdf, get_xml, get_content_from_zugferd

class ZUGFeRDWizard(Document):
    def read_file(self):
        file_path = os.path.join(frappe.utils.get_bench_path(), 'sites', frappe.utils.get_site_path()) + self.file
        xml_content = get_xml(file_path)
        invoice = get_content_from_zugferd(xml_content)
        return invoice
        
