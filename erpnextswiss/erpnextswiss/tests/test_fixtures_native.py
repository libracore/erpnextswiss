"""Check actual metadata after native fixture sync, not just install exit status."""

import json
from pathlib import Path
import unittest

import frappe


class TestNativeFixtureCompleteness(unittest.TestCase):
    def test_all_applicable_custom_fields_exist_after_install(self):
        missing = []
        checked = 0
        optional_targets = {"Expense Claim", "Salary Slip", "Employee"}
        directory = Path(frappe.get_app_path("erpnextswiss", "fixtures"))
        for file in sorted(directory.glob("*.json")):
            for field in json.loads(file.read_text(encoding="utf-8")):
                if field.get("doctype") != "Custom Field":
                    continue
                target = field["dt"]
                if not frappe.db.exists("DocType", target):
                    if target not in optional_targets:
                        missing.append("Missing required DocType: " + target)
                    continue
                checked += 1
                if not frappe.get_meta(target, cached=False).has_field(field["fieldname"]):
                    missing.append(field["name"])
        self.assertGreater(checked, 0, "The fixture inventory must not be empty")
        self.assertEqual(missing, [], "Applicable Swiss fields missing after native import")

    def test_existing_payment_workflow_columns_are_queryable(self):
        # These are existing workflow fields, not new payment behavior. LIMIT 0
        # verifies actual columns without reading or writing financial rows.
        frappe.db.sql("SELECT is_proposed FROM `tabPurchase Invoice` LIMIT 0")
        frappe.db.sql("SELECT camt_amount FROM `tabPayment Entry` LIMIT 0")
        frappe.db.sql("SELECT iban, bic, enable_lsv FROM `tabCustomer` LIMIT 0")
