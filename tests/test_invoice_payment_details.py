import unittest

from erpnextswiss.erpnextswiss.iso20022 import resolve_invoice_payment_details


class InvoicePaymentDetailsTests(unittest.TestCase):
    def test_invoice_iban_overrides_supplier_qr_iban(self):
        supplier_qr_iban = "CH98 3000 5248 2100 1701 C"
        self.assertEqual(
            resolve_invoice_payment_details(
                "CH86 0076 1649 7496 3200 2",
                supplier_qr_iban,
                supplier_qr_iban,
                "ESR",
            ),
            ("IBAN", "CH8600761649749632002", None),
        )

    def test_invoice_qr_iban_uses_qr_reference_payment_method(self):
        qr_iban = "CH98 3000 5248 2100 1701 C"
        self.assertEqual(
            resolve_invoice_payment_details(qr_iban, "", "", "IBAN"),
            ("ESR", "CH983000524821001701C", "CH983000524821001701C"),
        )

    def test_supplier_iban_is_used_when_invoice_override_is_blank(self):
        self.assertEqual(
            resolve_invoice_payment_details("", "CH86 0076 1649 7496 3200 2", "", "IBAN"),
            ("IBAN", "CH8600761649749632002", None),
        )
