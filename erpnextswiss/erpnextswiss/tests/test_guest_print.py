from types import SimpleNamespace
import unittest
from unittest.mock import patch

from frappe.exceptions import PermissionError

from erpnextswiss.erpnextswiss import guest_print


class GuestPrintSecurityTests(unittest.TestCase):
    def test_uses_document_share_key_validation(self):
        document = SimpleNamespace(doctype="Sales Invoice", name="SINV-0001")
        response = SimpleNamespace()

        with (
            patch.object(guest_print.frappe, "get_doc", return_value=document),
            patch.object(guest_print, "validate_key") as validate,
            patch.object(guest_print.frappe, "get_print", return_value=b"pdf") as get_print,
            patch.object(
                guest_print.frappe,
                "local",
                SimpleNamespace(response=response),
            ),
        ):
            guest_print.get_pdf_as_guest(
                "Sales Invoice",
                "SINV-0001",
                format="Standard",
                key="random-share-key",
            )

        validate.assert_called_once_with("random-share-key", document)
        get_print.assert_called_once_with(
            "Sales Invoice",
            "SINV-0001",
            "Standard",
            doc=None,
            as_pdf=True,
            no_letterhead=0,
        )
        self.assertEqual(response.filename, "SINV-0001.pdf")
        self.assertEqual(response.filecontent, b"pdf")
        self.assertEqual(response.type, "pdf")

    def test_rejects_predictable_legacy_document_signature(self):
        document = SimpleNamespace(
            doctype="Sales Invoice",
            name="SINV-0001",
            get_signature=lambda: "predictable-document-hash",
        )

        with (
            patch.object(guest_print.frappe, "get_doc", return_value=document),
            patch.object(
                guest_print,
                "validate_key",
                side_effect=PermissionError,
            ) as validate,
            patch.object(guest_print.frappe, "get_print") as get_print,
            self.assertRaises(PermissionError),
        ):
            guest_print.get_pdf_as_guest(
                "Sales Invoice",
                "SINV-0001",
                key=document.get_signature(),
            )

        validate.assert_called_once_with("predictable-document-hash", document)
        get_print.assert_not_called()
