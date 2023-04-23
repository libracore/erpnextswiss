# -*- coding: utf-8 -*-
# Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
# See license.txt
#
# Bench tests:
#  $ bench execute erpnextswiss.erpnextswiss.zugferd.zugferd_xml.create_zugferd_xml --kwargs "{'sales_invoice': 'SINV-00001'}"
#  $ bench execute erpnextswiss.erpnextswiss.zugferd.test_zugferd.create_pdf
#  $ bench execute erpnextswiss.erpnextswiss.zugferd.test_zugferd.read_pdf_from_file --kwargs "{'path': '/home/frappe/frappe-bench/sites/site1.local/public/files/zugferd_2p0_EN16931_Einfach.pdf'}"
#
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
from facturx import generate_facturx_from_binary
from erpnextswiss.erpnextswiss.zugferd.zugferd import import_pdf
from erpnextswiss.erpnextswiss.zugferd.facturx.facturx import generate_facturx_from_binary, get_facturx_xml_from_pdf, check_facturx_xsd
from PyPDF4 import PdfFileReader

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

def check_pdf_reader(path):
    pdf = PdfFileReader(path)
    print("{0}".format(pdf))
    return
    
def read_pdf_from_path(path):
    xml_content = import_pdf(path)
    print("{0}".format(xml_content))
    return

""" run this with a physical file path, e.g.
    $ bench execute erpnextswiss.erpnextswiss.zugferd.test_zugferd.read_pdf_from_file --kwargs "{'path': '/home/frappe/frappe-bench/sites/site1.local/public/files/zugferd_2p0_EN16931_Einfach.pdf'}"
"""
def read_pdf_from_file(path):
    f = open(path, "rb")
    content = f.read()
    xml_content = import_pdf(content)
    print("{0}".format(xml_content))
    return
