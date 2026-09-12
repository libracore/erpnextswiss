import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "banking_inventory", Path(__file__).resolve().parents[1] / "scripts" / "banking_readiness_inventory.py"
)
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class BankingInventoryTests(unittest.TestCase):
    def test_summary_is_aggregate_and_detects_mapping_defects(self):
        accounts = [
            {"name": "private-bank-name", "company": "private-company", "account": "ledger", "iban": "CH 123"},
            {"company": "private-company", "account": "ledger", "iban": "ch123"},
            {"company": "private-company", "account": "missing", "iban": ""},
            {"company": "other-company", "account": "invalid", "iban": "EUR123"},
            {"disabled": 1},
        ]
        ledgers = [
            {"name": "ledger", "company": "private-company", "account_type": "Bank", "account_currency": "CHF"},
            {"name": "invalid", "company": "wrong-company", "account_type": "Expense", "account_currency": "EUR", "is_group": 1},
        ]
        result = inventory.account_summary(accounts, ledgers)
        self.assertEqual(result["counts"], {
            "active": 4, "company_mismatch": 1, "disabled": 1, "duplicate_active_company_iban_groups": 1,
            "invalid_bank_ledger": 1, "missing_iban": 1, "missing_ledger": 1, "total": 5,
        })
        self.assertEqual(result["ledger_currencies"], {"CHF": 2, "EUR": 1})
        for private in ("private-bank-name", "private-company", "CH123", "EUR123", "wrong-company"):
            self.assertNotIn(private, json.dumps(result))

    def test_same_iban_in_separate_companies_is_not_combined(self):
        result = inventory.account_summary([
            {"company": "a", "iban": "CH123"}, {"company": "b", "iban": "CH123"},
            {"company": "a", "iban": "CH123", "disabled": 1},
        ], [])
        self.assertEqual(result["counts"]["duplicate_active_company_iban_groups"], 0)

    def test_scheduler_excludes_unrelated_methods_including_cron(self):
        result = inventory.banking_scheduler({
            "daily": ["app.notifications", "app.ebics.sync"],
            "hourly": ["app.search.reindex"],
            "cron": {"0 2 * * *": ["app.bank.cleanup", "app.mail.send"], "* * * * *": ["app.other"]},
        })
        self.assertEqual(result, {"daily": ["app.ebics.sync"], "cron": {"0 2 * * *": ["app.bank.cleanup"]}})

    def test_main_enforces_readonly_and_rolls_back_on_success_or_failure(self):
        for fail in (False, True):
            events = []
            frappe = SimpleNamespace(
                init=lambda **kwargs: events.append("init"), connect=lambda: events.append("connect"),
                set_user=lambda user: events.append("user:" + user), destroy=lambda: events.append("destroy"),
                db=SimpleNamespace(sql=lambda sql: events.append(sql), rollback=lambda: events.append("rollback")),
            )

            def read_report(_frappe):
                events.append("inventory")
                if fail:
                    raise ValueError("synthetic read failure")
                return {"read_only": True}

            with patch.dict(sys.modules, {"frappe": frappe}), patch.object(inventory, "inventory", read_report), \
                    patch.object(sys, "argv", ["inventory", "--site", "test.invalid", "--sites-path", "/tmp"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                if fail:
                    with self.assertRaisesRegex(ValueError, "synthetic read failure"):
                        inventory.main()
                else:
                    inventory.main()
            self.assertEqual(events, ["init", "connect", "START TRANSACTION READ ONLY", "user:Administrator",
                                      "inventory", "rollback", "destroy"])


if __name__ == "__main__":
    unittest.main()
