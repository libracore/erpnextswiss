import contextlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from frappe.exceptions import PermissionError

from erpnextswiss.erpnextswiss import guest_print
from erpnextswiss.erpnextswiss import print_format_safety


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
                doc='{"name":"SINV-0001","grand_total":0}',
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


class PrintFormatSafetyTests(unittest.TestCase):
    def test_download_pdf_normalizes_none_like_letterhead_fields(self):
        document = SimpleNamespace(doctype="Quotation", name="SAL-QTN-2026-00015")
        response = SimpleNamespace()

        with (
            patch.object(print_format_safety.frappe, "get_doc", return_value=document),
            patch.object(
                print_format_safety,
                "validate_print_permission",
            ) as validate_print_permission,
            patch.object(print_format_safety.frappe, "get_print") as get_print,
            patch.object(
                print_format_safety,
                "print_language",
                return_value=contextlib.nullcontext(),
            ) as print_language,
            patch.object(
                print_format_safety.frappe,
                "local",
                SimpleNamespace(response=response),
            ),
        ):
            get_print.return_value = b"pdf"

            print_format_safety.download_pdf(
                "Quotation",
                "SAL-QTN-2026-00015",
                format="Offerte DE Brutto",
                doc=None,
                no_letterhead="None",
                _lang="de",
                letterhead="None",
                pdf_generator="None",
            )

        validate_print_permission.assert_called_once_with(document)
        get_print.assert_called_once()
        called_kwargs = get_print.call_args.kwargs
        self.assertEqual(called_kwargs["doc"], document)
        self.assertEqual(called_kwargs["no_letterhead"], 0)
        self.assertIsNone(called_kwargs["letterhead"])
        self.assertNotIn("pdf_generator", called_kwargs)
        self.assertEqual(response.filename, "SAL-QTN-2026-00015.pdf")
        self.assertEqual(response.filecontent, b"pdf")
        self.assertEqual(response.type, "pdf")
        print_language.assert_called_once()
