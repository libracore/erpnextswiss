"""Offline safety regressions for the scheduled AKB retrieval and exact match."""

from datetime import date
from hashlib import sha256
import json
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

    def test_file_filter_keeps_only_new_xml_from_a_mixed_bank_delivery(self):
        old, new = xml(), xml().replace(b"statement-1", b"statement-2")
        payload = automation._archive_bytes({"old.xml": old, "new.xml": new})
        archive = automation._zip_from_receipt(payload, included_hashes={sha256(new).hexdigest()})
        from zipfile import ZipFile
        from io import BytesIO
        with ZipFile(BytesIO(archive)) as zipped:
            self.assertEqual(len(zipped.namelist()), 1)
            self.assertEqual(zipped.read(zipped.namelist()[0]), new)

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

    def test_invoice_reference_must_be_a_complete_token(self):
        self.assertTrue(automation._reference_mentions("SINV-1", "Payment for SINV-1 / thanks"))
        self.assertFalse(automation._reference_mentions("SINV-1", "Payment for SINV-12"))

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

    def test_replayed_entry_never_creates_a_second_payment(self):
        statement, entry = self._candidate()
        statement["account"] = "AKB bank account"
        connection = MagicMock(company="KT Wärmesysteme AG")
        with (patch.object(automation.frappe, "get_doc", return_value=self._invoice()),
              patch.object(automation.frappe.db, "exists", return_value="PAY-EXISTING"),
              patch("erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_payment_entry") as make_payment):
            self.assertFalse(automation._book_exact_match(connection, statement, entry, "EBICS-1"))
        make_payment.assert_not_called()

    def test_archive_is_committed_before_ebics_acknowledgement(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.company = "KT Wärmesysteme AG"
        connection.scope, connection.statement_btf_version = "CH", "08"
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
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation.frappe, "get_doc", side_effect=[record, record]),
              patch.object(automation.frappe.db, "commit", side_effect=lambda: events.append("commit")),
              patch.object(automation, "_verify_receipt", side_effect=lambda doc: events.append("readback")),
              patch.object(automation, "_acknowledge", side_effect=lambda conn, doc, **kw: events.append("ack"))):
            automation._download_pending(connection, date(2026, 9, 29))
        self.assertEqual(events, ["insert", "commit", "readback", "ack"])
        # The AKB current-pending request must not contain Start/End DateRange.
        self.assertEqual(len(client.BTD.call_args.args), 1)
        self.assertEqual(client.BTD.call_args.kwargs, {})

    def test_akb_legacy_statement_profile_uses_version_04_without_date_range(self):
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.scope, connection.statement_btf_version = "CH", "04"
        client = connection.get_client.return_value
        client.BTD.return_value = {"bank.xml": xml("camt.053.001.04")}
        client.last_trans_id = "BANK-TXN-LEGACY"
        record = MagicMock()
        record.name = "EBICS-LEGACY"
        record.insert.return_value = record
        created = []

        def get_doc(value, *args):
            if isinstance(value, dict):
                created.append(value)
            return record

        with (patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation, "_preview", return_value={"statements": []}) as preview,
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation.frappe, "get_doc", side_effect=get_doc),
              patch.object(automation.frappe.db, "commit"),
              patch.object(automation, "_verify_receipt"),
              patch.object(automation, "_acknowledge") as acknowledge):
            automation._download_pending(connection, date(2026, 9, 29))
        self.assertEqual(client.BTD.call_args.args[0].version, "04")
        self.assertEqual(len(client.BTD.call_args.args), 1)
        self.assertEqual(client.BTD.call_args.kwargs, {})
        self.assertEqual(created[0]["profile"], "camt.053.001.04")
        self.assertEqual(preview.call_args.kwargs["profile"], "camt.053.001.04")
        acknowledge.assert_called_once()

    def test_pending_receipt_is_replayed_without_second_download(self):
        connection = MagicMock()
        connection.name = "AKB"
        pending = MagicMock(requested_date="2026-09-28")
        events = []
        with (patch.object(automation, "_pending_receipt", return_value=pending),
              patch.object(automation, "_acknowledge", side_effect=lambda c, d: events.append("ack"))):
            automation._download_pending(connection, date(2026, 9, 29))
        self.assertEqual(events, ["ack"])
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

    def test_no_bank_data_does_not_claim_a_historical_day_was_synced(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.scope, connection.statement_btf_version = "CH", "08"
        connection.get_client.return_value.BTD.side_effect = Exception("EBICS_NO_DOWNLOAD_DATA_AVAILABLE")
        with patch.object(automation, "_pending_receipt", return_value=None):
            self.assertIsNone(automation._download_pending(connection, date(2026, 9, 29)))
        self.assertEqual(len(connection.get_client.return_value.BTD.call_args.args), 1)
        connection.save.assert_not_called()
        connection.get_client.return_value.confirm_download.assert_not_called()

    def test_current_sync_fetches_multiple_bank_files_for_same_day(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.enable_sync = 1
        connection.activated = 1
        connection.ebics_version = "H005"
        connection.scope = "CH"
        connection.statement_btf_version = "08"
        first = MagicMock(name="FIRST")
        second = MagicMock(name="SECOND")

        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", return_value=connection),
              patch.object(automation.frappe, "get_all", return_value=[]),
              patch.object(automation.frappe.utils, "getdate", return_value=date(2026, 9, 29)),
              patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation, "_download_pending", side_effect=[first, second, None]) as download,
              patch.object(automation, "_process_download") as process):
            result = automation.sync_connection("AKB")
        self.assertEqual(result, {"status": "ok", "downloads_fetched": 2})
        self.assertEqual(download.call_count, 3)
        self.assertTrue(all(call.args[:2] == (connection, date(2026, 9, 29))
                            for call in download.call_args_list))
        self.assertEqual([call.args[1] for call in process.call_args_list], [first, second])

    def test_current_sync_replays_older_pending_receipt_first(self):
        connection = MagicMock()
        connection.name = "AKB"
        connection.enable_sync = 1
        connection.activated = 1
        connection.ebics_version = "H005"
        connection.scope = "CH"
        connection.statement_btf_version = "08"
        pending = MagicMock(requested_date="2026-09-20", processing_state="Pending")

        def getdate(value=None):
            return date(2026, 9, 30) if value is None else (value if isinstance(value, date)
                                                             else date.fromisoformat(value))

        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", return_value=connection),
              patch.object(automation.frappe, "get_all", return_value=[]),
              patch.object(automation.frappe.utils, "getdate", side_effect=getdate),
              patch.object(automation, "_pending_receipt", return_value=pending),
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation, "_download_pending", side_effect=[pending, None]) as download,
              patch.object(automation, "_process_download") as process):
            automation.sync_connection("AKB")
        self.assertEqual(download.call_args_list[0].args, (connection, date(2026, 9, 20)))
        self.assertEqual(download.call_args_list[1].args[:2], (connection, date(2026, 9, 30)))
        process.assert_called_once_with(connection, pending)

    def test_repeated_bank_transaction_id_is_rejected_before_ack(self):
        connection = MagicMock(name="AKB")
        connection.name = "AKB"
        connection.scope, connection.statement_btf_version = "CH", "08"
        connection.get_client.return_value.BTD.return_value = {"bank.xml": "<Document/>"}
        connection.get_client.return_value.last_trans_id = "BANK-TXN-123"
        with (patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_preview", return_value={"statements": []}),
              patch.object(automation.frappe.db, "exists", return_value=True)):
            with self.assertRaisesRegex(BankFileError, "already archived"):
                automation._download_pending(connection, date(2026, 9, 29))
        connection.get_client.return_value.confirm_download.assert_not_called()

    def test_old_single_files_make_first_combined_delivery_a_duplicate(self):
        old, second = xml(), xml().replace(b"statement-1", b"statement-2")
        known = {sha256(old).hexdigest(): "EBICS-OLD-1",
                 sha256(second).hexdigest(): "EBICS-OLD-2"}
        metadata, new_hashes = automation._classify_files(
            automation._archive_bytes({"one.xml": old, "two.xml": second}), known)
        self.assertEqual(new_hashes, [])
        self.assertEqual(json.loads(metadata["duplicate_sources_json"]), known)
        self.assertIsNone(metadata["duplicate_of"])  # Two original receipts, not one.

    def test_mixed_delivery_archives_every_file_but_only_new_file_is_bookable(self):
        old, new = xml(), xml().replace(b"statement-1", b"statement-2")
        old_hash, new_hash = sha256(old).hexdigest(), sha256(new).hexdigest()
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.scope, connection.statement_btf_version = "CH", "08"
        client = connection.get_client.return_value
        client.BTD.return_value = {"old.xml": old, "new.xml": new}
        client.last_trans_id = "BANK-TXN-MIXED"
        record = MagicMock()
        record.name = "EBICS-MIXED"
        record.insert.return_value = record
        created = []

        def get_doc(value, *args):
            if isinstance(value, dict):
                created.append(value)
            return record

        known = {old_hash: "EBICS-OLD"}
        with (patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation, "_preview", return_value={"statements": []}),
              patch.object(automation.frappe, "get_doc", side_effect=get_doc),
              patch.object(automation.frappe.db, "commit"),
              patch.object(automation, "_verify_receipt"),
              patch.object(automation, "_acknowledge") as ack):
            automation._download_pending(connection, date(2026, 9, 29), known)
        self.assertEqual(json.loads(created[0]["new_file_hashes_json"]), [new_hash])
        self.assertEqual(json.loads(created[0]["duplicate_sources_json"]), {old_hash: "EBICS-OLD"})
        self.assertEqual(created[0]["processing_state"], "Pending")
        self.assertEqual(known[new_hash], "EBICS-MIXED")
        ack.assert_called_once()

    def test_repeat_with_new_transaction_id_is_archived_before_ack(self):
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.scope, connection.statement_btf_version = "CH", "08"
        old = xml()
        old_hash = sha256(old).hexdigest()
        record = MagicMock()
        record.name = "EBICS-REPEATED"
        record.insert.return_value = record
        record.processing_state = "Duplicate"
        record.duplicate_of = "EBICS-OLD"
        events = []
        record.insert.side_effect = lambda **kw: events.append("insert") or record
        client = connection.get_client.return_value
        client.BTD.return_value = {"repeated.xml": old}
        client.last_trans_id = "BANK-NEW-TRANSACTION-ID"
        created = []
        def get_doc(value, *args):
            if isinstance(value, dict):
                created.append(value)
            return record
        with (patch.object(automation.frappe, "get_doc", side_effect=get_doc),
              patch.object(automation.frappe.db, "exists", return_value=False),
              patch.object(automation.frappe.db, "commit", side_effect=lambda: events.append("commit")),
              patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_preview", return_value={"statements": []}),
              patch.object(automation, "_verify_receipt", side_effect=lambda doc: events.append("readback")),
              patch.object(automation, "_acknowledge", side_effect=lambda *a, **kw: events.append("ack"))):
            automation._download_pending(connection, date(2026, 9, 29), {old_hash: "EBICS-OLD"})
        self.assertEqual(created[0]["processing_state"], "Duplicate")
        self.assertEqual(json.loads(created[0]["new_file_hashes_json"]), [])
        self.assertEqual(events, ["insert", "commit", "readback", "ack"])
        client.BTD.assert_called_once()

    def test_two_identical_duplicate_payloads_stop_current_run(self):
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.enable_sync = connection.activated = 1
        connection.ebics_version, connection.scope, connection.statement_btf_version = "H005", "CH", "08"
        duplicate_one = MagicMock(processing_state="Duplicate", payload_sha256="same-sha")
        duplicate_two = MagicMock(processing_state="Duplicate", payload_sha256="same-sha")
        fresh = MagicMock(processing_state="Pending")
        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", return_value=connection),
              patch.object(automation.frappe, "get_all", return_value=[]),
              patch.object(automation.frappe.utils, "getdate", return_value=date(2026, 9, 29)),
              patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation, "_download_pending", side_effect=[duplicate_one, duplicate_two, fresh]) as download,
              patch.object(automation, "_process_download") as process):
            result = automation.sync_connection("AKB")
        self.assertEqual(result, {"status": "repeated_duplicate", "downloads_fetched": 0,
                                  "duplicate_receipts": 2})
        self.assertEqual(download.call_count, 2)
        process.assert_not_called()

    def test_one_old_duplicate_does_not_block_a_later_new_file(self):
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.enable_sync = connection.activated = 1
        connection.ebics_version, connection.scope, connection.statement_btf_version = "H005", "CH", "08"
        duplicate = MagicMock(processing_state="Duplicate", payload_sha256="old-sha")
        fresh = MagicMock(processing_state="Pending")
        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", return_value=connection),
              patch.object(automation.frappe, "get_all", return_value=[]),
              patch.object(automation.frappe.utils, "getdate", return_value=date(2026, 9, 29)),
              patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation, "_download_pending", side_effect=[duplicate, fresh, None]) as download,
              patch.object(automation, "_process_download") as process):
            result = automation.sync_connection("AKB")
        self.assertEqual(result, {"status": "ok", "downloads_fetched": 1, "duplicate_receipts": 1})
        self.assertEqual(download.call_count, 3)
        process.assert_called_once_with(connection, fresh)

    def test_next_run_can_process_a_new_file_after_prior_duplicate(self):
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.enable_sync = connection.activated = 1
        connection.ebics_version, connection.scope, connection.statement_btf_version = "H005", "CH", "08"
        fresh = MagicMock(processing_state="Pending")
        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", return_value=connection),
              patch.object(automation.frappe, "get_all", return_value=[]),
              patch.object(automation.frappe.utils, "getdate", return_value=date(2026, 9, 30)),
              patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation, "_download_pending", side_effect=[fresh, None]) as download,
              patch.object(automation, "_process_download") as process):
            result = automation.sync_connection("AKB")
        self.assertEqual(result, {"status": "ok", "downloads_fetched": 1})
        self.assertEqual(download.call_count, 2)
        process.assert_called_once_with(connection, fresh)

    def test_download_limit_is_visible_as_incomplete(self):
        connection = MagicMock(name="AKB", company="KT Wärmesysteme AG")
        connection.name = "AKB"
        connection.enable_sync = connection.activated = 1
        connection.ebics_version, connection.scope, connection.statement_btf_version = "H005", "CH", "08"
        fresh = MagicMock(processing_state="Pending")
        with (patch.object(automation, "MAX_DOWNLOADS_PER_RUN", 2),
              patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", return_value=connection),
              patch.object(automation.frappe, "get_all", return_value=[]),
              patch.object(automation.frappe.utils, "getdate", return_value=date(2026, 9, 30)),
              patch.object(automation, "_pending_receipt", return_value=None),
              patch.object(automation, "_known_files", return_value={}),
              patch.object(automation, "_download_pending", side_effect=[fresh, fresh]) as download,
              patch.object(automation, "_process_download")):
            result = automation.sync_connection("AKB")
        self.assertEqual(result, {"status": "limit_reached", "downloads_fetched": 2})
        self.assertEqual(download.call_count, 2)

    def test_accounting_preview_receives_only_new_file_hashes(self):
        old, new = xml(), xml().replace(b"statement-1", b"statement-2")
        payload = automation._archive_bytes({"old.xml": old, "new.xml": new})
        new_hash = sha256(new).hexdigest()
        record = MagicMock(ack_state="Confirmed", new_file_hashes_json=json.dumps([new_hash]))
        record.payload_json = payload.decode()
        record.payload_bytes = len(payload)
        record.payload_sha256 = sha256(payload).hexdigest()
        with patch.object(automation, "_preview", return_value={"statements": []}) as preview:
            self.assertEqual(automation._process_download(MagicMock(), record), {"booked": 0, "review": 0})
        self.assertEqual(preview.call_args.kwargs["included_hashes"], [new_hash])

    def test_historical_reconciliation_is_read_only_by_default(self):
        old, second = xml(), xml().replace(b"statement-1", b"statement-2")
        payloads = [automation._archive_bytes({"one.xml": old}),
                    automation._archive_bytes({"two.xml": second}),
                    automation._archive_bytes({"one.xml": old, "two.xml": second})]
        records = {}
        for index, payload in enumerate(payloads):
            row = MagicMock()
            row.name = f"EBICS-{index}"
            row.payload_json = payload.decode()
            row.payload_bytes = len(payload)
            row.payload_sha256 = sha256(payload).hexdigest()
            row.processing_state = "Review"
            row.booked_count = 0
            row.get.return_value = None
            records[row.name] = row
        connection = MagicMock(name="AKB")
        connection.name = "AKB"
        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", side_effect=lambda *args: connection if args[0] == "ebics Connection" else records[args[1]]),
              patch.object(automation.frappe, "get_all", return_value=list(records))):
            result = automation.reconcile_historical_receipts("AKB")
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["duplicate_receipts"], 1)
        self.assertEqual(result["receipts_checked"], 3)
        for record in records.values():
            record.db_set.assert_not_called()

    def test_historical_reconciliation_second_apply_is_idempotent(self):
        old, second = xml(), xml().replace(b"statement-1", b"statement-2")
        payloads = [automation._archive_bytes({"one.xml": old}),
                    automation._archive_bytes({"two.xml": second}),
                    automation._archive_bytes({"one.xml": old, "two.xml": second})]
        records = {}
        for index, payload in enumerate(payloads):
            row = MagicMock()
            row.name = f"EBICS-{index}"
            row.payload_json = payload.decode()
            row.payload_bytes = len(payload)
            row.payload_sha256 = sha256(payload).hexdigest()
            row.processing_state = "Review"
            row.booked_count = 0
            for key in ("file_hashes_json", "new_file_hashes_json", "duplicate_sources_json", "duplicate_of"):
                setattr(row, key, None)
            row.get.side_effect = lambda key, doc=row: getattr(doc, key, None)
            row.db_set.side_effect = lambda updates, commit=False, doc=row: [setattr(doc, key, value)
                                                                             for key, value in updates.items()]
            records[row.name] = row
        connection = MagicMock(name="AKB")
        connection.name = "AKB"
        with (patch.object(automation.frappe, "cache"),
              patch.object(automation.frappe, "get_doc", side_effect=lambda *args: connection if args[0] == "ebics Connection" else records[args[1]]),
              patch.object(automation.frappe, "get_all", return_value=list(records)),
              patch.object(automation.frappe.db, "commit") as commit):
            first = automation.reconcile_historical_receipts("AKB", apply=True)
            second_run = automation.reconcile_historical_receipts("AKB", apply=True)
            dry_run = automation.reconcile_historical_receipts("AKB")
        self.assertEqual(first["receipts_changed"], 3)
        self.assertEqual(first["duplicate_receipts"], 1)
        self.assertEqual(second_run["receipts_changed"], 0)
        self.assertEqual(dry_run["receipts_changed"], 0)
        self.assertEqual(records["EBICS-2"].processing_state, "Duplicate")
        self.assertEqual(commit.call_count, 2)
        for record in records.values():
            record.delete.assert_not_called()

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
