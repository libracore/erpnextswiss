# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and Contributors
# See license.txt
#
# Bench tests:
#  $ bench execute erpnextswiss.erpnextswiss.zugferd.zugferd_xml.create_zugferd_xml --kwargs "{'sales_invoice': 'SINV-00001'}"
#    bench execute erpnextswiss.erpnextswiss.zugferd.test_zugferd.create_pdf
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
from facturx import generate_facturx_from_binary

class TestZugferd(unittest.TestCase):
	pass




def create_pdf ():
    doctype = "Sales Invoice"
    name = "ACC-SINV-2020-00001"
    format=None
    doc=None
    no_letterhead=0
    html = frappe.get_print(doctype, name, format, doc=doc, no_letterhead=no_letterhead)
	
    pdf = get_pdf(html)
    xml = create_zugferd_xml(name)
    
    facturxPDF = generate_facturx_from_binary(pdf, xml)
    newFile = open("filename.pdf", "wb")
    newFile.write(facturxPDF)
    
    return
    
