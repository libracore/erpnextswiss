# -*- coding: utf-8 -*-
# Copyright (c) 2018-2026, libracore (https://www.libracore.com) and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

NS = {'e': "http://www.ech.ch/xmlns/eCH-0217/2"}
# activity, turnover, rate, tax (ESTV flat tax rate declaration Q2/2026)
Q2_ACTIVITIES = (
    ("Gesundheitsberatung/-praxis", 6384.03, 6.2, 395.81),
    ("Handel Normalsatz", 3520.48, 2.1, 73.93),
    ("Transport- und Umzugsunternehmen", 1950.00, 5.3, 103.35),
    ("Entsorgungsleistungen", 5800.67, 3.0, 174.02),
    ("Dienstleistungen Normalsatz", 198.55, 6.2, 12.31),
    ("Cafeterias Normalsatz", 10995.28, 5.3, 582.75),
    ("Wohnungsräumungen", 86850.00, 4.5, 3908.25),
    ("Cafeterias reduzierter Satz", 171.67, 0.6, 1.03),
)

def make_declaration(**kwargs):
    return frappe.get_doc(dict({
        'doctype': "VAT Declaration",
        'title': "Test",
        'company': "Test",
        'vat_type': "flat",
        'start_date': "2026-04-01",
        'end_date': "2026-06-30"
    }, **kwargs))

def render_transfer_file(doc):
    with patch("frappe.get_value", return_value="CHE-123.456.789 MWST"):
        return ElementTree.fromstring(doc.create_transfer_file()['content'].encode("utf-8"))

class TestVATDeclaration(unittest.TestCase):
    def test_flat_tax_rate_method(self):
        doc = make_declaration(
            total_revenue=2795657.85,
            non_taxable_revenue=100,
            non_taxable_services=2679787.17,
            amount_1=1000,
            rate_1=6.2,
            activities=[{'description': a, 'turnover': t, 'rate': r} for a, t, r, tax in Q2_ACTIVITIES],
            acquisition_taxes=[{'rate': 8.1, 'turnover': 1910.72}, {'rate': 2.6, 'turnover': 13.53}]
        )
        doc.calculate()
        for row, (a, t, r, tax) in zip(doc.activities, Q2_ACTIVITIES):
            self.assertAlmostEqual(row.tax, tax, places=2)
        self.assertAlmostEqual(doc.total_deductions, 2679787.17, places=2)
        self.assertAlmostEqual(doc.taxable_revenue, 115870.68, places=2)
        self.assertAlmostEqual(doc.activities_turnover, 115870.68, places=2)
        self.assertAlmostEqual(doc.activities_tax, 5251.45, places=2)
        self.assertAlmostEqual(doc.average_rate, 4.53, places=2)
        self.assertAlmostEqual(sum(r.tax for r in doc.acquisition_taxes), 155.12, places=2)
        self.assertAlmostEqual(doc.total_tax, 5406.57, places=2)
        self.assertAlmostEqual(doc.payable_tax, 5406.57, places=2)

    def test_net_tax_rate_method_before_2025(self):
        doc = make_declaration(start_date="2024-04-01", end_date="2024-06-30",
            amount_1=1000, rate_1=6.2, additional_tax=10, form_1050=5,
            activities=[{'description': "ignored", 'turnover': 1000, 'rate': 5}])
        doc.calculate()
        self.assertAlmostEqual(doc.total_tax, 72, places=2)
        self.assertAlmostEqual(doc.payable_tax, 67, places=2)

    def test_transfer_file_simple_method(self):
        doc = make_declaration(misc=100, misc_description="Test",
            activities=[
                {'activity_id': "12345", 'turnover': 1000, 'rate': 6.2},
                {'activity_id': "12345", 'turnover': 500, 'rate': 6.2},
                {'activity_id': "T0001", 'turnover': 200, 'rate': 2.1},
                {'turnover': 0, 'rate': 3.0}
            ],
            acquisition_taxes=[{'rate': 8.1, 'turnover': 1910.72}, {'rate': 2.6, 'turnover': 13.53}])
        doc.calculate()
        xml = render_transfer_file(doc)
        supplies = [(s.find("e:activityID", NS).text, s.find("e:taxRate", NS).text, s.find("e:turnover", NS).text)
            for s in xml.findall("e:simpleTaxRateMethod/e:suppliesPerTaxRate", NS)]
        self.assertEqual(supplies, [("12345", "6.20", "1500.00"), ("T0001", "2.10", "200.00")])
        self.assertEqual(len(xml.findall("e:simpleTaxRateMethod/e:acquisitionTax", NS)), 2)
        self.assertEqual(xml.find("e:turnoverComputation/e:variousDeduction/e:amountVariousDeduction", NS).text, "100.00")

    def test_transfer_file_requires_activity_id(self):
        doc = make_declaration(activities=[{'description': "Missing", 'turnover': 1000, 'rate': 6.2}])
        with self.assertRaisesRegex(frappe.ValidationError, "#1 Missing"):
            render_transfer_file(doc)

    def test_transfer_file_before_2025(self):
        doc = make_declaration(start_date="2024-04-01", end_date="2024-06-30", amount_1=1000, rate_1=6.2)
        xml = render_transfer_file(doc)
        self.assertEqual(len(xml.findall("e:netTaxRateMethod/e:suppliesPerTaxRate", NS)), 4)
        self.assertEqual(xml.find("e:netTaxRateMethod/e:acquisitionTax/e:taxRate", NS).text, "8.10")
