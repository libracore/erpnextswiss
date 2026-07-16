import unittest

import frappe

from erpnextswiss.setup.install import _prepare_workspace_data, _workspace_target_exists
from erpnextswiss.erpnextswiss.zugferd.zugferd import import_pdf


class TestV16Compatibility(unittest.TestCase):
    def test_workspace_sanitizer_skips_missing_doctype_targets(self):
        workspace = _prepare_workspace_data(
            {
                "doctype": "Workspace",
                "name": "ERPNextSwiss Test",
                "links": [
                    {
                        "label": "Sales Invoices",
                        "link_to": "Sales Invoice",
                        "link_type": "DocType",
                        "type": "Link",
                    },
                    {
                        "label": "Missing Optional DocType",
                        "link_to": "Definitely Missing Optional DocType",
                        "link_type": "DocType",
                        "type": "Link",
                    },
                ],
                "shortcuts": [
                    {
                        "label": "Sales Invoices",
                        "link_to": "Sales Invoice",
                        "type": "DocType",
                    },
                    {
                        "label": "Missing Optional DocType",
                        "link_to": "Definitely Missing Optional DocType",
                        "type": "DocType",
                    },
                ],
                "content": '[{"type":"shortcut","data":{"shortcut_name":"Sales Invoices"}},'
                '{"type":"shortcut","data":{"shortcut_name":"Missing Optional DocType"}}]',
            }
        )

        self.assertEqual([link["label"] for link in workspace["links"]], ["Sales Invoices"])
        self.assertEqual([shortcut["label"] for shortcut in workspace["shortcuts"]], ["Sales Invoices"])
        self.assertNotIn("Missing Optional DocType", workspace["content"])

    def test_report_shortcut_is_skipped_when_ref_doctype_is_missing(self):
        if frappe.db.exists("Report", "Annual Salary Sheet") and not frappe.db.exists("DocType", "Salary Slip"):
            self.assertFalse(_workspace_target_exists("Report", "Annual Salary Sheet"))

    def test_zugferd_import_pdf_compatibility_api_is_available(self):
        self.assertTrue(callable(import_pdf))
