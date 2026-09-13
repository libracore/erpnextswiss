import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("fixture_inventory",
    Path(__file__).resolve().parents[1] / "scripts" / "swiss_fixture_inventory.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class FixtureInventoryTests(unittest.TestCase):
    def test_drift_missing_and_optional_targets_are_distinguished_without_values(self):
        fields = [{"doctype": "Custom Field", "name": "Customer-iban", "dt": "Customer",
                   "fieldname": "iban", "fieldtype": "Data", "default": None, "options": None},
                  {"doctype": "Custom Field", "name": "Customer-missing", "dt": "Customer"},
                  {"doctype": "Custom Field", "name": "Expense Claim-is_proposed", "dt": "Expense Claim"}]
        actual = {**fields[0], "default": "private-bank-value", "options": "private-choice-value"}
        frappe = SimpleNamespace(db=SimpleNamespace(exists=lambda dt, name:
            name == ("Customer" if dt == "DocType" else "Customer-iban")),
            get_doc=lambda *_: actual, get_meta=lambda *_: SimpleNamespace(has_field=lambda _: True))
        with TemporaryDirectory() as directory:
            (Path(directory) / "custom_field.json").write_text(json.dumps(fields), encoding="utf-8")
            result = inventory.inspect(frappe, directory)
        self.assertEqual(result["candidate_fields"], 3)
        self.assertEqual(result["applicable_fields"], 2)
        self.assertEqual(result["missing_custom_fields"], ["Customer-missing"])
        self.assertEqual(result["optional_target_absent"], ["Expense Claim-is_proposed"])
        self.assertEqual(result["definition_drift"], [{"name": "Customer-iban", "attributes": ["default", "options"]}])
        self.assertTrue(result["requires_review"])
        self.assertNotIn("private-bank-value", json.dumps(result))
        self.assertNotIn("private-choice-value", json.dumps(result))

    def test_empty_inventory_fails_and_missing_core_target_requires_review(self):
        frappe = SimpleNamespace(db=SimpleNamespace(exists=lambda *_: False),
            get_meta=lambda *_: SimpleNamespace(has_field=lambda _: True))
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                inventory.inspect(frappe, directory)
            file = Path(directory) / "custom_field.json"
            file.write_text(json.dumps([{"doctype": "Custom Field", "name": "Customer-iban", "dt": "Customer"}]), encoding="utf-8")
            result = inventory.inspect(frappe, directory)
            self.assertEqual(result["missing_required_doctypes"], ["Customer"])
            self.assertTrue(result["requires_review"])

    def test_all_supported_source_attributes_are_compared_but_not_record_metadata(self):
        expected = {"doctype": "Custom Field", "name": "Customer-iban", "dt": "Customer",
            "fieldname": "iban", "bold": 0, "unique": 0, "ignore_user_permissions": 0,
            "new_supported_attribute": "source", "removed_attribute": 0, "modified": "old"}
        actual = {**expected, "bold": 1, "unique": 1, "ignore_user_permissions": 1,
            "new_supported_attribute": "private-value", "modified": "new"}
        frappe = SimpleNamespace(db=SimpleNamespace(exists=lambda *_: True), get_doc=lambda *_: actual,
            get_meta=lambda *_: SimpleNamespace(has_field=lambda field: field != "removed_attribute"))
        with TemporaryDirectory() as directory:
            (Path(directory) / "custom_field.json").write_text(json.dumps([expected]), encoding="utf-8")
            result = inventory.inspect(frappe, directory)
        self.assertEqual(result["definition_drift"], [{"name": "Customer-iban",
            "attributes": ["bold", "ignore_user_permissions", "new_supported_attribute", "unique"]}])
        self.assertEqual(result["unsupported_source_attributes"], ["removed_attribute"])
        self.assertNotIn("private-value", json.dumps(result))

    def test_main_enforces_readonly_and_rollback_on_success_and_failure(self):
        for fail in (False, True):
            events = []
            frappe = SimpleNamespace(init=lambda **_: events.append("init"), connect=lambda: events.append("connect"),
                set_user=lambda _: events.append("admin"), destroy=lambda: events.append("destroy"),
                db=SimpleNamespace(sql=lambda query: events.append(query), rollback=lambda: events.append("rollback")))

            def inspect(*_):
                events.append("inspect")
                if fail:
                    raise ValueError("synthetic read failure")
                return {"read_only": True}

            with patch.dict(sys.modules, {"frappe": frappe}), patch.object(inventory, "inspect", inspect), \
                    contextlib.redirect_stdout(io.StringIO()):
                args = ["--site", "test.invalid", "--sites-path", "/tmp", "--fixtures-dir", "/candidate"]
                if fail:
                    with self.assertRaisesRegex(ValueError, "synthetic read failure"):
                        inventory.main(args)
                else:
                    inventory.main(args)
            self.assertEqual(events, ["init", "connect", "START TRANSACTION READ ONLY", "admin", "inspect", "rollback", "destroy"])
