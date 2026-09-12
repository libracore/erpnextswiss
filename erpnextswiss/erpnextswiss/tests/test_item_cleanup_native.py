import unittest
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.handler import is_valid_http_method
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from erpnextswiss.scripts.item_tools import purge_supplier_hints_from_item_descriptions


class TestItemCleanupNative(unittest.TestCase):
    def setUp(self):
        self.user = frappe.session.user
        frappe.set_user("Administrator")
        self.savepoint = "cleanup_" + uuid4().hex
        frappe.db.savepoint(self.savepoint)
        self.item_code = "KT-CLEANUP-TEST-" + uuid4().hex
        if not frappe.db.exists("UOM", "Nos"):
            frappe.get_doc({"doctype": "UOM", "uom_name": "Nos"}).insert()
        group_name = "KT-CLEANUP-GROUP-" + uuid4().hex
        group = frappe.get_doc({"doctype": "Item Group", "item_group_name": group_name,
                               "parent_item_group": "All Item Groups", "is_group": 0}).insert()
        self.before = "Technical title<br>Supplier: Synthetic supplier<br>Technical detail"
        frappe.get_doc({"doctype": "Item", "item_code": self.item_code, "item_name": self.item_code,
                        "item_group": group.name, "stock_uom": "Nos", "is_stock_item": 0,
                        "description": self.before}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback(save_point=self.savepoint)
        frappe.set_user(self.user)

    def test_real_http_method_registry_denies_get_and_accepts_post(self):
        for method in ("GET", "POST"):
            builder = EnvironBuilder(method=method)
            request = Request(builder.get_environ())
            try:
                with patch.object(frappe.local, "request", request, create=True):
                    if method == "GET":
                        with self.assertRaises(frappe.PermissionError):
                            is_valid_http_method(purge_supplier_hints_from_item_descriptions)
                    else:
                        is_valid_http_method(purge_supplier_hints_from_item_descriptions)
            finally:
                request.close()
                builder.close()

    def test_guest_cannot_preview_or_apply(self):
        frappe.set_user("Guest")
        for apply in (0, 1):
            with self.assertRaises(frappe.PermissionError):
                purge_supplier_hints_from_item_descriptions(apply=apply, item_codes=[self.item_code])
        frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Item", self.item_code, "description"), self.before)

    def test_admin_preview_and_apply_are_transactional(self):
        preview = purge_supplier_hints_from_item_descriptions(item_codes=[self.item_code])
        self.assertEqual((preview["checked"], preview["changed"], preview["applied"]), (1, 1, False))
        self.assertEqual(frappe.db.get_value("Item", self.item_code, "description"), self.before)
        before_apply = "apply_" + uuid4().hex
        frappe.db.savepoint(before_apply)
        result = purge_supplier_hints_from_item_descriptions(apply=1, item_codes=[self.item_code])
        self.assertTrue(result["applied"])
        self.assertEqual(frappe.db.get_value("Item", self.item_code, "description"), "Technical title<br>Technical detail")
        # A helper-internal commit would remove this savepoint and make this rollback fail.
        frappe.db.rollback(save_point=before_apply)
        self.assertEqual(frappe.db.get_value("Item", self.item_code, "description"), self.before)
