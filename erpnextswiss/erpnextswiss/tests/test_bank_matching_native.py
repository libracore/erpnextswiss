"""Native permission/query regressions; synthetic rows, no GL or bank operations."""

import unittest
from unittest.mock import patch
from uuid import uuid4

import frappe
from bs4 import BeautifulSoup
from frappe.model.document import Document

from erpnextswiss.erpnextswiss.page.bank_wizard import bank_wizard
from erpnextswiss.erpnextswiss.tests.test_bank_file_admission import xml
from erpnextswiss.scripts.bank_matching_scope import BankMatchingScope


class TestBankMatchingNative(unittest.TestCase):
    def setUp(self):
        self.original_user = frappe.session.user
        frappe.set_user("Administrator")
        self.key = uuid4().hex[:12]
        self.savepoint = "bank_" + self.key
        frappe.db.savepoint(self.savepoint)
        self.addCleanup(self.cleanup_rows)
        self.company_a, self.company_b = "KT-BANK-A-" + self.key, "KT-BANK-B-" + self.key
        for name in (self.company_a, self.company_b):
            self.row("Company", name, company_name=name, abbr=name[-12:], default_currency="CHF", country="Switzerland")
        self.account_a, self.account_other, self.account_b = ["KT-BANK-" + label + self.key for label in ("A-", "OTHER-", "B-")]
        for name, company in ((self.account_a, self.company_a), (self.account_other, self.company_a), (self.account_b, self.company_b)):
            self.row("Account", name, account_name=name, company=company, account_type="Bank", root_type="Asset",
                     report_type="Balance Sheet", is_group=0, disabled=0, account_currency="CHF", iban="CH9300762011623852957")
        self.invoice_a, self.invoice_b = "KT-SINV-A-" + self.key, "KT-SINV-B-" + self.key
        for name, company in ((self.invoice_a, self.company_a), (self.invoice_b, self.company_b)):
            self.row("Sales Invoice", name, company=company, docstatus=1, customer="Synthetic Counterparty",
                     customer_name="Synthetic Counterparty", outstanding_amount=12.34, grand_total=12.34)
        self.settings = frappe._dict(debug_mode=1, always_use_entry_transaction_type=1, always_use_entry_amount=0,
                                     numeric_only_debtor_matching=0, ignore_special_characters=0)

    def row(self, doctype, name, **values):
        # These fixture rows exercise real SQL/permissions, not invoice validation
        # or accounting submission. They are removed by the enclosing savepoint.
        values = {"name": name, "owner": "Administrator", **values}
        columns = ",".join("`" + field + "`" for field in values)
        frappe.db.sql("INSERT INTO `tab" + doctype + "` (" + columns + ") VALUES ("
                      + ",".join(["%s"] * len(values)) + ")", tuple(values.values()))

    def cleanup_rows(self):
        frappe.set_user("Administrator")
        try:
            frappe.db.rollback(save_point=self.savepoint)
        finally:
            frappe.set_user(self.original_user)

    def entries(self, detailed=True, reference=None):
        reference = reference or self.invoice_a + " " + self.invoice_b
        details = ("<NtryDtls><TxDtls><Refs><AcctSvcrRef>shared-test-reference</AcctSvcrRef></Refs>"
                   "<RmtInf><Ustrd>" + reference + "</Ustrd></RmtInf></TxDtls></NtryDtls>") if detailed else ""
        text = ("<Ntry><Amt Ccy=\"CHF\">12.34</Amt><CdtDbtInd>CRDT</CdtDbtInd>"
                "<BookgDt><Dt>2026-09-12</Dt></BookgDt><AcctSvcrRef>shared-test-reference</AcctSvcrRef>"
                "<BkTxCd><Prtry><Cd>TEST</Cd></Prtry></BkTxCd>" + details + "</Ntry>")
        return BeautifulSoup(text, "lxml").find_all("ntry")

    def test_same_reference_only_suppresses_same_active_account_payment(self):
        self.row("Payment Entry", "KT-PE-B-" + self.key, company=self.company_b,
                 reference_no="shared-test-reference", paid_to=self.account_b, docstatus=1)
        self.row("Payment Entry", "KT-PE-OTHER-" + self.key, company=self.company_a,
                 reference_no="shared-test-reference", paid_to=self.account_other, docstatus=1)
        self.row("Payment Entry", "KT-PE-CANCELLED-" + self.key, company=self.company_a,
                 reference_no="shared-test-reference", paid_to=self.account_a, docstatus=2)
        for detailed in (False, True):
            result = bank_wizard.read_camt_transactions(self.entries(detailed), self.account_a, self.settings, read_only=True)
            self.assertEqual(len(result), 1)
        self.row("Payment Entry", "KT-PE-A-" + self.key, company=self.company_a,
                 reference_no="shared-test-reference", paid_from=self.account_a, docstatus=1)
        for detailed in (False, True):
            self.assertEqual(bank_wizard.read_camt_transactions(self.entries(detailed), self.account_a,
                                                               self.settings, read_only=True), [])

    def test_invoice_matches_remain_in_selected_company_even_with_legacy_bypass_flag(self):
        for account, expected in ((self.account_a, self.invoice_a), (self.account_b, self.invoice_b)):
            result = bank_wizard.read_camt_transactions(self.entries(), account, self.settings,
                                                       skip_company_filter=True, read_only=True)
            self.assertEqual(result[0]["invoice_matches"], [expected])
            self.assertEqual(result[0]["matched_amount"], 12.34)

    def test_same_iban_keeps_explicit_company_account_and_return_contract(self):
        for account in (self.account_a, self.account_b):
            with patch.object(bank_wizard, "render_transactions", return_value="unchanged-renderer"):
                result = bank_wizard.read_camt053(xml().decode(), account)
            self.assertEqual(result, {"transactions": [], "html": "unchanged-renderer", "bank": account})
        with self.assertRaises(frappe.ValidationError):
            bank_wizard.read_camt053(xml().decode().replace("CH9300762011623852957", "CH5604835012345678009"), self.account_a)

    def test_read_only_matcher_keeps_rules_and_makes_no_write_commit_or_error_log(self):
        self.row("Bank Wizard Pattern", "KT-PATTERN-" + self.key, disabled=0, target_field="Amount", operator="=", value="12.34")
        with patch.object(Document, "insert", side_effect=AssertionError("No insert")), \
                patch.object(Document, "save", side_effect=AssertionError("No save")), \
                patch.object(Document, "submit", side_effect=AssertionError("No submit")), \
                patch.object(frappe.db, "commit", side_effect=AssertionError("No commit")), \
                patch.object(frappe, "log_error", side_effect=AssertionError("No database log")):
            result = bank_wizard.read_camt_transactions(self.entries(), self.account_a, self.settings, debug=True, read_only=True)
        self.assertEqual(result[0]["pattern"], "KT-PATTERN-" + self.key)
        self.assertEqual(result[0]["invoice_matches"], [self.invoice_a])

    def test_native_company_user_permission_applies_to_scope_and_candidate_queries(self):
        email = "kt-bank-" + self.key + "@example.invalid"
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Synthetic bank test",
                        "enabled": 1, "send_welcome_email": 0, "user_type": "System User",
                        "roles": [{"role": "Accounts User"}]}).insert()
        frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Company",
                        "for_value": self.company_a, "apply_to_all_doctypes": 1}).insert()
        frappe.set_user(email)
        scope = BankMatchingScope(self.account_a)
        self.assertEqual([row.name for row in scope.records("Sales Invoice", {"name": ["in", [self.invoice_a, self.invoice_b]]}, ["name"])], [self.invoice_a])
        with self.assertRaises(frappe.PermissionError):
            BankMatchingScope(self.account_b)
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            BankMatchingScope(self.account_a)

    def test_disabled_account_and_optional_hr_have_explicit_behavior(self):
        frappe.db.set_value("Account", self.account_other, "disabled", 1)
        with self.assertRaises(frappe.ValidationError):
            BankMatchingScope(self.account_other)
        scope = BankMatchingScope(self.account_a)
        for doctype in ("Employee", "Expense Claim"):
            if not frappe.db.exists("DocType", doctype):
                self.assertEqual(scope.records(doctype, {}, ["name"]), [])

    def test_child_proposal_lookup_checks_parent_company_first(self):
        proposal = "KT-PROPOSAL-" + self.key
        self.row("Payment Proposal", proposal, company=self.company_b, docstatus=0)
        self.row("Payment Proposal Payment", "KT-PROPOSAL-ROW-" + self.key, parent=proposal,
                 parenttype="Payment Proposal", parentfield="payments", idx=1, receiver="Synthetic")
        scope = BankMatchingScope(self.account_a)
        self.assertEqual(scope.records("Payment Proposal Payment", {"parent": proposal, "idx": 1}, ["name"]), [])
        other_scope = BankMatchingScope(self.account_b)
        self.assertEqual(len(other_scope.records("Payment Proposal Payment", {"parent": proposal, "idx": 1}, ["name"])), 1)
