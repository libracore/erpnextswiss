"""Check actual metadata after native fixture sync, not just install exit status."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

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

    def test_native_export_preserves_groups_and_excludes_foreign_fields(self):
        from frappe.utils.fixtures import export_fixtures

        source = Path(frappe.get_app_path("erpnextswiss", "fixtures"))
        expected = {
            file.name: {row["name"] for row in json.loads(file.read_text(encoding="utf-8"))
                        if frappe.db.exists("DocType", row["dt"])}
            for file in source.glob("*.json")
        }
        get_app_path = frappe.get_app_path
        savepoint = "fixture_export_" + uuid4().hex
        frappe.db.savepoint(savepoint)
        try:
            # The exporter reads Custom Field records. db_insert deliberately
            # avoids schema DDL, so the synthetic foreign row rolls back fully.
            fieldname = "foreign_fixture_" + uuid4().hex
            frappe.get_doc(doctype="Custom Field", name="Customer-" + fieldname,
                dt="Customer", fieldname=fieldname, fieldtype="Data",
                label="Foreign fixture probe").db_insert()
            with TemporaryDirectory() as directory:
                def export_path(app, *parts):
                    if app == "erpnextswiss" and parts and parts[0] == "fixtures":
                        return str(Path(directory).joinpath(*parts))
                    return get_app_path(app, *parts)

                with patch.object(frappe, "get_app_path", side_effect=export_path):
                    first = None
                    for _ in range(2):
                        export_fixtures("erpnextswiss")
                        files = {file.name: file for file in (Path(directory) / "fixtures").glob("*.json")}
                        self.assertEqual(set(files), set(expected))
                        for name, file in files.items():
                            rows = json.loads(file.read_text(encoding="utf-8"))
                            self.assertEqual({row["name"] for row in rows}, expected[name])
                        snapshot = {name: file.read_bytes() for name, file in files.items()}
                        if first is not None:
                            self.assertEqual(snapshot, first)
                        first = snapshot
        finally:
            frappe.db.rollback(save_point=savepoint)
