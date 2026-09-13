"""Native permission/query regressions; synthetic rows, no GL or bank operations."""

import unittest
from unittest.mock import patch
from uuid import uuid4

import frappe
from bs4 import BeautifulSoup
from frappe.model.document import Document
from lxml import etree

from erpnextswiss.erpnextswiss.page.bank_wizard import bank_wizard
from erpnextswiss.erpnextswiss.tests.test_bank_file_admission import PROFILE, xml, zipped
from erpnextswiss.erpnextswiss.tests.test_bank_camt_preview import detailed_xml
from erpnextswiss.scripts.bank_camt_preview import preview_camt_archive
from erpnextswiss.scripts.bank_file_admission import BankFileError, PROFILES
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

    def preview(self, payload, profile=PROFILE, accounts=None):
        return preview_camt_archive(payload, profile, company=self.company_a, accounts=accounts or [self.account_a])

    def test_archive_preview_runs_existing_matcher_for_both_profiles_and_utf16(self):
        for profile in PROFILES:
            root = etree.fromstring(detailed_xml(profile, remark=self.invoice_a + ' & <literal>', foreign_amount=True))
            prefixed = etree.Element(root.tag, nsmap={'bank': root.nsmap[None]})
            prefixed.extend(root)
            content = etree.tostring(prefixed, encoding='UTF-16', xml_declaration=True)
            # Real settings are read by the adapter. Configure values inside the
            # test savepoint; no changed settings survive the test.
            frappe.db.set_single_value('ERPNextSwiss Settings', 'always_use_entry_amount', 0)
            result = self.preview(zipped([('statement.xml', content)]), profile)
            entry = result['statements'][0]['entries'][0]
            self.assertEqual(entry['issues'], [])
            self.assertEqual(entry['candidates'][0]['invoice_matches'], [self.invoice_a])
            self.assertEqual(entry['candidates'][0]['amount'], 12.34)
            self.assertEqual(entry['candidates'][0]['currency'], 'CHF')
            self.assertEqual(entry['candidates'][0]['transaction_reference'], self.invoice_a + ' & <literal>')
            self.assertEqual(entry['candidates'][0]['party_name'], 'Test & Co <Bank> / Customer')
            self.assertEqual(result['archive'].files[0].content, content)

    def test_archive_preflights_late_account_currency_and_permissions_before_matching(self):
        valid = detailed_xml(remark=self.invoice_a)
        for invalid in [valid.replace(b'CH9300762011623852957', b'CH5604835012345678009'),
                        xml(currency='EUR', entries=True), b'<broken>']:
            with patch.object(bank_wizard, 'read_camt_transactions', side_effect=AssertionError('No early matching')):
                with self.assertRaises(BankFileError):
                    self.preview(zipped([('valid.xml', valid), ('late.xml', invalid)]))
        with patch.object(bank_wizard, 'read_camt_transactions', side_effect=AssertionError('No cross-company matching')):
            with self.assertRaises(BankFileError):
                self.preview(zipped(), accounts=[self.account_b])
            with self.assertRaises(BankFileError):
                self.preview(zipped(), accounts=[self.account_a, self.account_other])
            frappe.set_user('Guest')
            with self.assertRaises(frappe.PermissionError):
                self.preview(zipped())

    def test_archive_maps_each_statement_to_its_configured_currency_account(self):
        frappe.db.set_value('Account', self.account_other, 'account_currency', 'EUR')
        payload = zipped([('chf.xml', xml(entries=True)), ('eur.xml', xml(currency='EUR', entries=True))])
        result = self.preview(payload, accounts=[self.account_a, self.account_other])
        self.assertEqual([(s['account'], s['currency']) for s in result['statements']],
                         [(self.account_a, 'CHF'), (self.account_other, 'EUR')])
        self.assertEqual([s['entries'][0]['candidates'][0]['currency'] for s in result['statements']], ['CHF', 'EUR'])
        ambiguous = xml().replace(b'<Ccy>CHF</Ccy>', b'')
        with self.assertRaises(BankFileError):
            self.preview(zipped([('ambiguous.xml', ambiguous)]), accounts=[self.account_a, self.account_other])

    def test_archive_never_writes_even_with_debug_enabled_and_preserves_zero_entries(self):
        frappe.db.set_single_value('ERPNextSwiss Settings', 'debug_mode', 1)
        with patch.object(Document, 'insert', side_effect=AssertionError('No insert')), \
                patch.object(Document, 'save', side_effect=AssertionError('No save')), \
                patch.object(Document, 'submit', side_effect=AssertionError('No submit')), \
                patch.object(frappe.db, 'commit', side_effect=AssertionError('No commit')), \
                patch.object(frappe, 'log_error', side_effect=AssertionError('No log')):
            result = self.preview(zipped([('empty.xml', xml()), ('data.xml', detailed_xml())]))
        self.assertEqual(len(result['statements']), 2)
        self.assertEqual(result['statements'][0]['entries'], [])
        self.assertEqual(len(result['statements'][0]['balances']), 1)
        self.assertEqual(len(result['statements'][1]['entries'][0]['candidates']), 1)

    def test_archive_retains_pending_reversal_missing_date_and_batch_review(self):
        cases = [(xml(entries=True).replace(b'BOOK', b'PDNG'), 'not_booked'),
                 (xml(entries=True).replace(b'<Sts>', b'<RvslInd>true</RvslInd><Sts>'), 'reversal_requires_review'),
                 (xml(entries=True).replace(b'<BookgDt><Dt>2026-09-12</Dt></BookgDt>', b''), 'missing_booking_date'),
                 (detailed_xml(amounts=('10', '20')).replace(b'>30<', b'>31<'), 'detail_sum_differs_from_booking')]
        frappe.db.set_single_value('ERPNextSwiss Settings', 'always_use_entry_amount', 0)
        with patch.object(bank_wizard, 'read_camt_transactions', side_effect=AssertionError('No guessed match')):
            for content, issue in cases:
                entry = self.preview(zipped([('review.xml', content)]))['statements'][0]['entries'][0]
                self.assertEqual(entry['matching_state'], 'review_required')
                self.assertIn(issue, entry['issues'])
                self.assertEqual(entry['candidates'], [])

    def test_archive_batch_results_keep_exact_entry_provenance_and_suppressed_rows(self):
        frappe.db.set_single_value('ERPNextSwiss Settings', 'always_use_entry_amount', 0)
        root = etree.fromstring(detailed_xml(amounts=('10', '20'), reference='batch'))
        ns = {'b': root.nsmap[None]}
        statement = root.find('b:BkToCstmrStmt/b:Stmt', ns)
        extra = etree.fromstring(detailed_xml(reference='later')).find('.//b:Ntry', ns)
        statement.append(extra)
        self.row('Payment Entry', 'KT-PE-PREVIEW-' + self.key, company=self.company_a,
                 paid_to=self.account_a, reference_no='batch-0', docstatus=1)
        result = self.preview(zipped([('batch.xml', etree.tostring(root))]))
        first, second = result['statements'][0]['entries']
        self.assertEqual(first['detail_count'], 2)
        self.assertEqual(first['suppressed_by_existing_matcher'], 1)
        self.assertEqual([c['unique_reference'] for c in first['candidates']], ['batch-1'])
        self.assertEqual([c['unique_reference'] for c in second['candidates']], ['later-0'])
        self.assertEqual(first['candidates'][0]['amount'], 20)
        self.assertEqual(second['candidates'][0]['amount'], 12.34)

    def test_archive_does_not_replace_missing_amount_with_unrelated_instructed_amount(self):
        root = etree.fromstring(detailed_xml())
        ns = {'b': root.nsmap[None]}
        tag = lambda name: '{' + ns['b'] + '}' + name
        detail = root.find('.//b:TxDtls', ns)
        detail.remove(detail.find('b:Amt', ns))
        amounts = etree.Element(tag('AmtDtls'))
        instructed = etree.SubElement(amounts, tag('InstdAmt'))
        etree.SubElement(instructed, tag('Amt'), Ccy='USD').text = '1000'
        detail.insert(1, amounts)
        frappe.db.set_single_value('ERPNextSwiss Settings', 'always_use_entry_amount', 0)
        result = self.preview(zipped([('amount.xml', etree.tostring(root))]))
        candidate = result['statements'][0]['entries'][0]['candidates'][0]
        self.assertEqual((candidate['amount'], candidate['currency']), (12.34, 'CHF'))

    def test_archive_debit_reuses_supplier_invoice_matching_with_current_company(self):
        supplier = 'KT-SUPPLIER-' + self.key
        self.row('Supplier', supplier, supplier_name=supplier, disabled=0)
        invoice = 'KT-PINV-' + self.key
        self.row('Purchase Invoice', invoice, company=self.company_a, docstatus=1,
                 supplier=supplier, outstanding_amount=12.34, grand_total=12.34, bill_no='bill-' + self.key)
        self.row('Purchase Invoice', invoice + '-FOREIGN', company=self.company_b, docstatus=1,
                 supplier=supplier, outstanding_amount=12.34, grand_total=12.34, bill_no='bill-' + self.key)
        root = etree.fromstring(detailed_xml(remark='bill-' + self.key))
        ns = {'b': root.nsmap[None]}
        root.find('.//b:Ntry/b:CdtDbtInd', ns).text = 'DBIT'
        debtor = root.find('.//b:Dbtr', ns)
        debtor.tag = '{' + ns['b'] + '}Cdtr'
        debtor.find('b:Pty/b:Nm', ns).text = supplier
        result = self.preview(zipped([('debit.xml', etree.tostring(root))]))
        candidate = result['statements'][0]['entries'][0]['candidates'][0]
        self.assertEqual(candidate['credit_debit'], 'DBIT')
        self.assertEqual(candidate['party_match'], supplier)
        self.assertEqual(candidate['invoice_matches'], [invoice])
        self.assertEqual(candidate['matched_amount'], 12.34)
