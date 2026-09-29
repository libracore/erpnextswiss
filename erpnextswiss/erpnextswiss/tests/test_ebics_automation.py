"""Offline safety regressions for the scheduled AKB retrieval and exact match."""

from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from erpnextswiss.erpnextswiss import ebics_automation as automation
from erpnextswiss.erpnextswiss.tests.test_bank_file_admission import xml
from erpnextswiss.scripts.bank_file_admission import BankFileError
from erpnextswiss.scripts.bank_camt_preview import prepare_camt_archive


class TestEbicsAutomation(TestCase):
    def test_payload_is_deterministic_and_keeps_xml_bytes(self):
        one = automation._archive_bytes({"z": b"<Document>one</Document>", "a": "<Document>two</Document>"})
        two = automation._archive_bytes({"a": "<Document>two</Document>", "z": b"<Document>one</Document>"})
        self.assertEqual(one, two)
        archive = automation._zip_from_receipt(one)
        from zipfile import ZipFile
        from io import BytesIO
        with ZipFile(BytesIO(archive)) as zipped:
            self.assertEqual(zipped.namelist(), ["statement-000.xml", "statement-001.xml"])
            self.assertEqual(zipped.read("statement-000.xml"), b"<Document>two</Document>")

    def test_account_binding_must_be_explicit_and_current(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.company = "KT Wärmesysteme AG"
        with patch.object(automation, "get_site_config", return_value={}):
            with self.assertRaises(BankFileError):
                automation._accounts(connection)
        account = frappe._dict(name="BANK", company=connection.company, account_type="Bank",
                               disabled=0, is_group=0, iban="CH123", account_currency="CHF")
        config = {"ebics_auto_accounts": {"version": 1, "bindings": {"AKB": ["BANK"]}}}
        with (patch.object(automation, "get_site_config", return_value=config),
              patch.object(automation.frappe, "get_doc", return_value=account)):
            self.assertEqual(automation._accounts(connection), ["BANK"])

    def test_non_utf8_xml_fails_before_bank_receipt(self):
        with self.assertRaises(UnicodeDecodeError):
            automation._archive_bytes({"a": b"\xff"})

    def test_sdk_xml_roundtrips_through_strict_camt_admission(self):
        content = xml(entries=True)
        receipt = automation._archive_bytes({"bank-export.xml": content})
        archive, statements = prepare_camt_archive(automation._zip_from_receipt(receipt), automation.PROFILE)
        self.assertEqual(archive.files[0].content, content)
        self.assertEqual(len(statements), 1)

    def test_exact_match_rejects_unbalanced_statement(self):
        statement, entry = self._candidate()
        statement["balance_check"] = "mismatch"
        self.assertIsNone(automation._strict_invoice_candidate(MagicMock(), statement, entry))

    def test_exact_match_rejects_unverified_bank_reference(self):
        statement, entry = self._candidate()
        entry["candidates"][0]["unique_reference"] = "fabricated-reference"
        self.assertIsNone(automation._strict_invoice_candidate(MagicMock(), statement, entry))

    def test_exact_match_rejects_multiple_candidates(self):
        statement, entry = self._candidate()
        entry["candidates"].append(dict(entry["candidates"][0]))
        self.assertIsNone(automation._strict_invoice_candidate(MagicMock(), statement, entry))

    def test_fractional_cent_is_not_rounded_into_an_auto_booking(self):
        statement, entry = self._candidate()
        entry["amount"] = "100.001"
        self.assertIsNone(automation._strict_invoice_candidate(MagicMock(), statement, entry))

    def test_exact_match_rejects_foreign_company(self):
        statement, entry = self._candidate()
        connection = MagicMock(company="KT Wärmesysteme AG")
        invoice = frappe._dict(name="SINV-1", docstatus=1, company="Another company",
                               customer="CUST-1", outstanding_amount=100, currency="CHF")
        with patch.object(automation.frappe, "get_doc", return_value=invoice):
            self.assertIsNone(automation._strict_invoice_candidate(connection, statement, entry))

    def test_exact_match_accepts_one_matching_open_invoice(self):
        statement, entry = self._candidate()
        connection = MagicMock(company="KT Wärmesysteme AG")
        invoice = self._invoice()
        with patch.object(automation.frappe, "get_doc", return_value=invoice):
            accepted = automation._strict_invoice_candidate(connection, statement, entry)
        self.assertEqual(accepted[1], "Sales Invoice")
        self.assertEqual(accepted[2].name, "SINV-1")

    def test_auto_booking_never_submits_a_difference(self):
        statement, entry = self._candidate()
        statement["account"] = "AKB bank account"
        connection = MagicMock(company="KT Wärmesysteme AG")
        invoice = self._invoice()
        payment = MagicMock()
        payment.docstatus = 0
        payment.company = connection.company
        payment.party = "CUST-1"
        payment.paid_amount = 100
        payment.received_amount = 100
        payment.difference_amount = 0.01
        payment.unallocated_amount = 0
        payment.deductions = []
        payment.references = [frappe._dict(reference_doctype="Sales Invoice", reference_name="SINV-1",
                                           allocated_amount=100)]
        with (patch.object(automation.frappe, "get_doc", side_effect=[invoice, payment]),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation.frappe.db, "savepoint"),
              patch.object(automation.frappe.db, "rollback") as rollback,
              patch("erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_accounts",
                    return_value={"receivable_account": "AR"}),
              patch("erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_payment_entry",
                    return_value={"payment_entry": "PAY-1"}) as make_payment):
            with self.assertRaises(BankFileError):
                automation._book_exact_match(connection, statement, entry, "EBICS-1")
        self.assertFalse(make_payment.call_args.kwargs["auto_submit"])
        payment.submit.assert_not_called()
        rollback.assert_called_once()

    def test_auto_booking_submits_one_exact_payment(self):
        statement, entry = self._candidate()
        statement["account"] = "AKB bank account"
        connection = MagicMock(company="KT Wärmesysteme AG")
        invoice = self._invoice()
        payment = MagicMock()
        payment.docstatus = 0
        payment.company = connection.company
        payment.party = "CUST-1"
        payment.paid_amount = 100
        payment.received_amount = 100
        payment.difference_amount = 0
        payment.unallocated_amount = 0
        payment.deductions = []
        payment.references = [frappe._dict(reference_doctype="Sales Invoice", reference_name="SINV-1",
                                           allocated_amount=100)]
        with (patch.object(automation.frappe, "get_doc", side_effect=[invoice, payment]),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation.frappe.db, "savepoint"),
              patch.object(automation.frappe.db, "commit") as commit,
              patch("erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_accounts",
                    return_value={"receivable_account": "AR"}),
              patch("erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_payment_entry",
                    return_value={"payment_entry": "PAY-1"}) as make_payment):
            self.assertTrue(automation._book_exact_match(connection, statement, entry, "EBICS-1"))
        self.assertFalse(make_payment.call_args.kwargs["auto_submit"])
        self.assertEqual(make_payment.call_args.kwargs["paid_to"], "AKB bank account")
        payment.submit.assert_called_once()
        commit.assert_called_once()

    def test_archive_is_committed_before_ebics_acknowledgement(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.company = "KT Wärmesysteme AG"
        client = connection.get_client.return_value
        client.BTD.return_value = {"bank.xml": "<Document/>"}
        client.last_trans_id = "BANK-TXN-123"
        record = MagicMock(name="EBICS-record")
        events = []
        record.insert.side_effect = lambda **kw: events.append("insert") or record
        record.name = "EBICS-test"
        with (patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation, "_preview", return_value={"statements": []}),
              patch.object(automation.frappe, "get_doc", side_effect=[record, record]),
              patch.object(automation.frappe.db, "commit", side_effect=lambda: events.append("commit")),
              patch.object(automation, "_verify_receipt", side_effect=lambda doc: events.append("readback")),
              patch.object(automation, "_acknowledge", side_effect=lambda conn, doc, **kw: events.append("ack")),
              patch.object(automation, "_advance", side_effect=lambda conn, day: events.append("cursor"))):
            automation._download_day(connection, date(2026, 9, 28))
        self.assertEqual(events, ["insert", "commit", "readback", "ack", "cursor"])

    def test_pending_receipt_is_replayed_without_second_download(self):
        connection = MagicMock()
        connection.name = "AKB"
        pending = MagicMock(requested_date="2026-09-28")
        events = []
        with (patch.object(automation, "_pending_receipt", return_value=pending),
              patch.object(automation, "_acknowledge", side_effect=lambda c, d: events.append("ack")),
              patch.object(automation, "_advance", side_effect=lambda c, d: events.append("cursor"))):
            automation._download_day(connection, date(2026, 9, 28))
        self.assertEqual(events, ["ack", "cursor"])
        connection.get_client.assert_not_called()

    def test_bank_receipt_is_confirmed_only_after_readback(self):
        connection = MagicMock()
        client = MagicMock()
        record = MagicMock(ack_state="Pending", bank_transaction_id="BANK-TXN-123")
        events = []
        client.confirm_download.side_effect = lambda **kw: events.append("bank_ack")
        record.db_set.side_effect = lambda *args, **kw: events.append("erp_ack")
        with patch.object(automation, "_verify_receipt", side_effect=lambda doc: events.append("readback")):
            automation._acknowledge(connection, record, client=client)
        self.assertEqual(events, ["readback", "bank_ack", "erp_ack"])
        connection.get_client.assert_not_called()

    def test_no_bank_data_advances_date_without_payment(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.get_client.return_value.BTD.side_effect = Exception("EBICS_NO_DOWNLOAD_DATA_AVAILABLE")
        events = []
        with (patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation, "_advance", side_effect=lambda conn, day: events.append(day))):
            self.assertIsNone(automation._download_day(connection, date(2026, 9, 28)))
        self.assertEqual(events, [date(2026, 9, 28)])
        connection.get_client.return_value.confirm_download.assert_not_called()

    @staticmethod
    def _candidate():
        candidate = {"amount": 100, "matched_amount": 100, "currency": "CHF",
                     "credit_debit": "CRDT", "date": "2026-09-28", "unique_reference": "BANK-REF-1",
                     "invoice_matches": ["SINV-1"], "party_match": "CUST-1",
                     "transaction_reference": "SINV-1"}
        statement = {"balance_check": "matched", "currency": "CHF"}
        entry = {"issues": [], "detail_count": 1, "candidates": [candidate], "amount": "100.00",
                 "credit_debit": "CRDT", "booking_date": "2026-09-28", "reference": "BANK-REF-1",
                 "entry_reference": None}
        return statement, entry

    @staticmethod
    def _invoice():
        return frappe._dict(name="SINV-1", docstatus=1, company="KT Wärmesysteme AG",
                            customer="CUST-1", outstanding_amount=100, currency="CHF",
                            bill_no=None, esr_reference=None, esr_reference_number=None,
                            reference_number_full=None)
