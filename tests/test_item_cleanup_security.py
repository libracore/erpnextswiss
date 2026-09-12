import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch


class ItemCleanupSecurityTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.role = "System Manager"
        self.denied = set()
        self.items = [
            {"name": "test-A", "description": "Title<br>Lieferant: Internal supplier<br>Detail"},
            {"name": "test-B", "description": "Title\nSupplier: Other supplier\nDetail"},
            {"name": "test-C", "description": "Already clean"},
        ]

        def whitelist(**options):
            def decorate(function):
                function.test_whitelist_options = options
                return function
            return decorate

        def only_for(role):
            self.events.append(("role", role))
            if self.role != role:
                raise PermissionError("restricted maintenance")

        def get_list(doctype, **kwargs):
            self.events.append(("list", doctype, kwargs))
            return self.items

        def get_doc(doctype, name):
            def check_permission(action):
                self.events.append(("permission", name, action))
                if name in self.denied:
                    raise PermissionError("document denied")
            return SimpleNamespace(check_permission=check_permission)

        def fail(message, error):
            raise error(message)

        frappe = SimpleNamespace(
            whitelist=whitelist, only_for=only_for, get_list=get_list, get_doc=get_doc,
            ValidationError=ValueError, throw=fail,
            db=SimpleNamespace(set_value=lambda *args: self.events.append(("write", *args))),
        )
        spec = importlib.util.spec_from_file_location(
            "item_cleanup_under_test", Path(__file__).resolve().parents[1] / "erpnextswiss" / "scripts" / "item_tools.py"
        )
        self.module = importlib.util.module_from_spec(spec)
        patcher = patch.dict(sys.modules, {"frappe": frappe})
        patcher.start()
        self.addCleanup(patcher.stop)
        spec.loader.exec_module(self.module)
        self.cleanup = self.module.purge_supplier_hints_from_item_descriptions

    def test_only_post_and_no_unprivileged_read_or_write(self):
        self.assertEqual(self.cleanup.test_whitelist_options, {"methods": ["POST"]})
        for role in ("Guest", "Accounts User", "Portal User"):
            self.role = role
            self.events.clear()
            with self.assertRaises(PermissionError):
                self.cleanup(apply=1)
            self.assertEqual(self.events, [("role", "System Manager")])

    def test_preview_keeps_filtering_and_does_not_write(self):
        result = self.cleanup(item_codes="test-A, test-B", limit=5)
        self.assertEqual((result["checked"], result["changed"], result["applied"]), (3, 2, False))
        self.assertEqual(len(result["preview"]), 2)
        self.assertEqual(self.events[1], ("list", "Item", {
            "filters": {"disabled": 0, "name": ["in", ["test-A", "test-B"]]},
            "fields": ["name", "description"], "limit_page_length": 5,
        }))
        self.assertFalse(any(event[0] in ("write", "permission") for event in self.events))

    def test_write_preflights_every_item_and_does_not_commit(self):
        result = self.cleanup(apply="1")
        self.assertTrue(result["applied"])
        self.assertEqual(self.events[1][2]["limit_page_length"], 0)
        self.assertEqual(self.events[2:], [
            ("permission", "test-A", "write"), ("permission", "test-B", "write"),
            ("write", "Item", "test-A", "description", "Title<br>Detail"),
            ("write", "Item", "test-B", "description", "Title<br>Detail"),
        ])

    def test_late_permission_failure_prevents_all_writes(self):
        self.denied.add("test-B")
        with self.assertRaises(PermissionError):
            self.cleanup(apply=1)
        self.assertFalse(any(event[0] == "write" for event in self.events))

    def test_invalid_apply_never_queries_items(self):
        for apply in (2, -1):
            self.events.clear()
            with self.assertRaises(ValueError):
                self.cleanup(apply=apply)
            self.assertEqual(self.events, [("role", "System Manager")])


if __name__ == "__main__":
    unittest.main()
