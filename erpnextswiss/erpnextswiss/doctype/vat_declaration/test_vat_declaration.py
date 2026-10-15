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

# Item Tax Templates with VAT declaration codes and their turnover in the period
CODE_TEMPLATES = (
    ("HANS21 - T", "Calculation sheet", 2.1, "12345", 1000.0),
    ("CAR06 - T", "Calculation sheet", 0.6, "12346", 200.0),
    ("WOH45 - T", "Calculation sheet", 4.5, "12347", 0.0),
    ("Ausgenommen - T", "230", None, None, 5000.0),
    ("Spende - T", "910", None, None, 300.0),
)

def get_values(doc, queries=None, lines=None):
    # runs get_values with the templates above and the given VAT queries {name: total} instead of database records
    queries = queries or {}
    templates = [frappe._dict(name=n, title=n.split(" - ")[0], vat_declaration_code=c, description=None,
        flat_tax_rate=r, estv_activity_id=a) for n, c, r, a, t in CODE_TEMPLATES]
    with patch.object(type(doc), "get_code_templates", return_value=templates), \
            patch.object(type(doc), "get_template_turnovers", return_value={n: t for n, c, r, a, t in CODE_TEMPLATES}), \
            patch.object(type(doc), "get_view_sum", side_effect=lambda view_name, column="base_grand_total": queries[view_name]), \
            patch.object(frappe.db, "exists", side_effect=lambda doctype, name=None: name in queries), \
            patch.object(type(doc), "get_lines_without_template", return_value=lines or []):
        doc.get_values()

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

    def test_item_tax_template_codes(self):
        doc = make_declaration(revenue_abroad=7, activities=[
            {'description': "Leistungen 2024", 'activity_id': "T0001", 'rate': 2.1, 'turnover': 100}])
        get_values(doc)
        self.assertAlmostEqual(doc.total_revenue, 6200, places=2)
        self.assertAlmostEqual(doc.non_taxable_services, 5000, places=2)
        self.assertAlmostEqual(doc.donations, 300, places=2)
        self.assertAlmostEqual(doc.revenue_abroad, 7, places=2)
        self.assertEqual([(r.activity_id, r.rate, r.turnover) for r in doc.activities],
            [("T0001", 2.1, 100), ("12345", 2.1, 1000), ("12346", 0.6, 200)])
        self.assertAlmostEqual(doc.activities_tax, 2.1 + 21 + 1.2, places=2)

    def test_vat_queries_take_precedence(self):
        doc = make_declaration(activities=[{'item_tax_template': "CAR06 - T", 'vat_query': "Cafeteria", 'turnover': 0}])
        get_values(doc, {'viewVAT_230': 4000, 'Cafeteria': 250})
        self.assertAlmostEqual(doc.non_taxable_services, 4000, places=2)
        self.assertAlmostEqual(doc.total_revenue, 6200, places=2)
        self.assertEqual([(r.item_tax_template, r.turnover) for r in doc.activities],
            [("HANS21 - T", 1000), ("CAR06 - T", 250)])

    def test_unassigned_taxable_revenue(self):
        doc = make_declaration(total_revenue=1500, activities=[{'activity_id': "12345", 'rate': 2.1, 'turnover': 1000}])
        with patch("frappe.msgprint") as msgprint:
            doc.validate()
            self.assertEqual(msgprint.call_count, 1)
            doc.total_revenue = 1000
            doc.validate()
            self.assertEqual(msgprint.call_count, 1)

    def test_lines_without_template(self):
        with patch("frappe.msgprint") as msgprint:
            get_values(make_declaration())
            self.assertEqual(msgprint.call_count, 0)
            get_values(make_declaration(), lines=[frappe._dict(name="SINV-1", base_net_amount=100)])
            self.assertEqual(msgprint.call_count, 1)
            self.assertIn("SINV-1", msgprint.call_args[0][0])
