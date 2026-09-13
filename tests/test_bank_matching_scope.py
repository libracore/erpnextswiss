import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch


class BankMatchingScopeTests(unittest.TestCase):
    def setUp(self):
        self.account = SimpleNamespace(name="bank-A", account_type="Bank", disabled=0, is_group=0,
                                       company="company-A", check_permission=Mock(), get=lambda key: "CH93 0076")
        self.company = SimpleNamespace(check_permission=Mock())
        self.frappe = SimpleNamespace(
            only_for=Mock(), get_doc=Mock(side_effect=lambda dt, name: self.account if dt == "Account" else self.company),
            get_list=Mock(return_value=[]), get_all=Mock(return_value=[]),
            has_permission=Mock(return_value=True), db=SimpleNamespace(exists=Mock(return_value=True)),
            ValidationError=ValueError,
        )
        def fail(message, kind):
            raise kind(message)
        self.frappe.throw = fail
        spec = importlib.util.spec_from_file_location("bank_scope_under_test", Path(__file__).resolve().parents[1]
                                                      / "erpnextswiss/scripts/bank_matching_scope.py")
        self.module = importlib.util.module_from_spec(spec)
        patcher = patch.dict(sys.modules, {"frappe": self.frappe})
        patcher.start()
        self.addCleanup(patcher.stop)
        spec.loader.exec_module(self.module)

    def test_role_account_and_company_permissions_precede_matching(self):
        scope = self.module.BankMatchingScope("bank-A")
        self.assertEqual((scope.account, scope.company), ("bank-A", "company-A"))
        self.account.check_permission.assert_called_once_with("read")
        self.company.check_permission.assert_called_once_with("read")
        for denied in (self.frappe.only_for, self.account.check_permission, self.company.check_permission):
            denied.side_effect = PermissionError("denied")
            with self.assertRaises(PermissionError):
                self.module.BankMatchingScope("bank-A")
            denied.side_effect = None
        self.frappe.get_list.assert_not_called()
        self.frappe.get_all.assert_not_called()

    def test_disabled_group_nonbank_and_missing_account_are_rejected(self):
        for field, value in [("disabled", 1), ("is_group", 1), ("account_type", "Receivable"), ("company", None)]:
            old = getattr(self.account, field)
            setattr(self.account, field, value)
            with self.assertRaises(ValueError):
                self.module.BankMatchingScope("bank-A")
            setattr(self.account, field, old)
        for value in (None, "", " "):
            with self.assertRaises(ValueError):
                self.module.BankMatchingScope(value)

    def test_explicit_iban_must_match_no_account_lookup(self):
        scope = self.module.BankMatchingScope("bank-A")
        scope.check_iban("ch930076")
        with self.assertRaises(ValueError):
            scope.check_iban("another-iban")
        self.frappe.get_list.assert_not_called()

    def test_company_filter_is_added_without_mutating_or_replacing_input(self):
        scope = self.module.BankMatchingScope("bank-A")
        for doctype in scope.COMPANY_RECORDS:
            supplied = {"company": "company-B", "docstatus": ["!=", 2]}
            scope.records(doctype, supplied, ["name"])
            options = self.frappe.get_list.call_args.kwargs
            self.assertIn(["company", "=", "company-A"], options["filters"])
            self.assertIn(["company", "=", "company-B"], options["filters"])
            self.assertEqual(supplied, {"company": "company-B", "docstatus": ["!=", 2]})
            self.assertEqual(options["limit_page_length"], 0)
        supplied = [["outstanding_amount", ">", 0]]
        scope.records("Sales Invoice", supplied, ["name"])
        self.assertEqual(supplied, [["outstanding_amount", ">", 0]])

    def test_duplicate_payment_requires_account_and_company_and_is_not_cancelled(self):
        scope = self.module.BankMatchingScope("bank-A")
        scope.records("Payment Entry", {"reference_no": "same-reference"}, ["name"])
        options = self.frappe.get_list.call_args.kwargs
        self.assertIn(["company", "=", "company-A"], options["filters"])
        self.assertIn(["docstatus", "!=", 2], options["filters"])
        self.assertEqual(options["or_filters"], [["paid_from", "=", "bank-A"], ["paid_to", "=", "bank-A"]])

    def test_optional_hr_is_absent_or_unauthorized_without_breaking_other_matches(self):
        scope = self.module.BankMatchingScope("bank-A")
        self.frappe.db.exists.return_value = False
        self.assertEqual(scope.records("Employee", {}, ["name"]), [])
        self.frappe.db.exists.return_value = True
        self.frappe.has_permission.return_value = False
        self.assertEqual(scope.records("Expense Claim", {}, ["name"]), [])
        self.frappe.get_list.assert_not_called()

    def test_proposal_children_require_exact_authorized_parent_in_company(self):
        scope = self.module.BankMatchingScope("bank-A")
        self.assertEqual(scope.records("Payment Proposal Payment", {"parent": "proposal-B", "idx": 1}, ["name"]), [])
        self.frappe.get_all.assert_not_called()
        self.frappe.get_list.assert_called_once_with("Payment Proposal", filters={"name": "proposal-B", "company": "company-A"},
                                                    fields=["name"], limit_page_length=1)
        self.frappe.get_list.return_value = [{"name": "proposal-A"}]
        scope.records("Payment Proposal Payment", {"parent": "proposal-A", "idx": 2}, ["name"])
        self.frappe.get_all.assert_called_once_with("Payment Proposal Payment", filters={"parent": "proposal-A", "idx": 2}, fields=["name"])

    def test_known_configuration_keeps_existing_engine_but_unknown_sources_fail(self):
        scope = self.module.BankMatchingScope("bank-A")
        scope.records("Bank Wizard Pattern", {"disabled": 0}, ["name", "value"])
        self.frappe.get_all.assert_called_once_with("Bank Wizard Pattern", filters={"disabled": 0}, fields=["name", "value"])
        with self.assertRaises(ValueError):
            scope.records("User", {}, ["name"])
