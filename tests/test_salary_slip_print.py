import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

try:
    from jinja2.sandbox import SandboxedEnvironment
except ImportError:
    SandboxedEnvironment = None


ROOT = Path(__file__).resolve().parents[1]


class SalaryPrintTests(unittest.TestCase):
    def setUp(self):
        self.frappe = MagicMock()
        self.setter = MagicMock()
        ps = ModuleType("frappe.custom.doctype.property_setter.property_setter")
        ps.make_property_setter = self.setter
        self.modules = patch.dict(sys.modules, {"frappe": self.frappe, ps.__name__: ps})
        self.modules.start()
        spec = importlib.util.spec_from_file_location("salary_print_test_subject", ROOT / "erpnextswiss/setup/salary_slip_print.py")
        self.subject = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.subject)

    def tearDown(self):
        self.modules.stop()

    def test_optional_hrms(self):
        self.frappe.db.exists.return_value = False
        self.subject.sync_salary_slip_print_format()
        self.frappe.get_doc.assert_not_called()
        self.setter.assert_not_called()

    def test_other_company_not_changed(self):
        self.frappe.db.exists.side_effect = [True, False]
        self.subject.sync_salary_slip_print_format()
        self.frappe.get_doc.assert_not_called()

    def test_create_sets_only_salary_default(self):
        self.frappe.db.exists.side_effect = [True, True, False]
        self.frappe.get_meta.return_value = SimpleNamespace(default_print_format="Standard")
        self.subject.sync_salary_slip_print_format()
        definition = self.frappe.get_doc.call_args.args[0]
        self.assertEqual(definition["doc_type"], "Salary Slip")
        self.frappe.get_doc.return_value.insert.assert_called_once_with(ignore_permissions=True)
        self.setter.assert_called_once_with("Salary Slip", None, "default_print_format", "KT Lohnabrechnung", "Data", for_doctype=True)
        self.frappe.db.commit.assert_not_called()

    def test_repeat_migration_is_noop(self):
        definition = self.subject.print_format_definition()
        record = MagicMock()
        record.doc_type = "Salary Slip"
        record.get.side_effect = definition.get
        self.frappe.db.exists.return_value = True
        self.frappe.get_doc.return_value = record
        self.frappe.get_meta.return_value = SimpleNamespace(default_print_format=self.subject.FORMAT_NAME)
        self.subject.sync_salary_slip_print_format()
        record.save.assert_not_called()
        record.insert.assert_not_called()
        self.setter.assert_not_called()

    def test_owned_template_drift_is_restored(self):
        definition = self.subject.print_format_definition()
        old = dict(definition, html="old template")
        record = MagicMock()
        record.doc_type = "Salary Slip"
        record.get.side_effect = old.get
        self.frappe.db.exists.return_value = True
        self.frappe.get_doc.return_value = record
        self.frappe.get_meta.return_value = SimpleNamespace(default_print_format=self.subject.FORMAT_NAME)
        self.subject.sync_salary_slip_print_format()
        record.update.assert_called_once_with({"html": definition["html"]})
        record.save.assert_called_once_with(ignore_permissions=True)

    def test_doctype_collision_refuses_overwrite(self):
        self.frappe.db.exists.return_value = True
        record = self.frappe.get_doc.return_value
        record.doc_type = "Sales Invoice"
        self.frappe.throw.side_effect = ValueError("collision")
        with self.assertRaises(ValueError):
            self.subject.sync_salary_slip_print_format()
        record.save.assert_not_called()

    def test_template_does_not_guess_rates_or_recalculate(self):
        html = self.subject.print_format_definition()["html"]
        for token in ("money(doc.net_pay)", "money(doc.gross_pay)", "money(doc.total_deduction)", "money(row.amount)", "disable_rounded_total"):
            self.assertIn(token, html)
        for token in ("Salary Structure", "7000", "0.053", "letter_head.content", "fonts.googleapis", "0000000", "frappe.db.set_value", "frappe.get_all"):
            self.assertNotIn(token, html)
        for token in ("doc.employee_name|e", "employee_address|e", "doc.bank_account_no|e", "ENTWURF", "STORNIERT", "keine Zahlungsbestätigung", "table-header-group"):
            self.assertIn(token, html)

    def test_both_update_hooks_and_package_include_template(self):
        source = (ROOT / "erpnextswiss/setup/install.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("    sync_salary_slip_print_format()"), 2)
        self.assertIn("recursive-include erpnextswiss *.html", (ROOT / "MANIFEST.in").read_text())


class AttrDict(dict):
    __getattr__ = dict.get


@unittest.skipUnless(SandboxedEnvironment, "Jinja is available in native Frappe / rendering environments")
class SalaryTemplateRenderTests(unittest.TestCase):
    def setUp(self):
        self.doc = AttrDict(company="Test AG", employee="TEST-01", employee_name="Erika Muster", name="TEST-SLIP", docstatus=1, start_date="2026-12-01", end_date="2026-12-31", posting_date="2026-12-31", currency="CHF", gross_pay=12000, total_deduction=1200, net_pay=10800, rounded_total=10800, earnings=[AttrDict(salary_component="Basic", amount=8000), AttrDict(salary_component="13. Monatslohn", amount=4000)], deductions=[AttrDict(salary_component="AHV/IV/EO Arbeitnehmer", amount=1200)], employer_contributions=[], bank_name=None, bank_account_no=None)
        self.rounding_disabled = 1
        self.frappe = SimpleNamespace(
            get_doc=lambda *args: AttrDict(company_logo=None, email=None, website=None),
            db=SimpleNamespace(get_value=lambda *args, **kwargs: None, get_single_value=lambda *args: self.rounding_disabled),
            utils=SimpleNamespace(getdate=date.fromisoformat, formatdate=lambda value, _: date.fromisoformat(value).strftime("%d.%m.%Y")),
        )
        self.template = SandboxedEnvironment(autoescape=False).from_string((ROOT / "erpnextswiss/templates/print_formats/kt_salary_slip.html").read_text(encoding="utf-8"))

    def render(self):
        return self.template.render(doc=self.doc, frappe=self.frappe)

    def test_december_13th_saved_amounts(self):
        html = self.render()
        for expected in ("Dezember 2026", "13. Monatslohn", "4'000.00", "12'000.00", "10'800.00"):
            self.assertIn(expected, html)
        self.assertNotIn("ENTWURF</span>", html)
        self.assertNotIn("STORNIERT</span>", html)
        self.assertNotIn("Zahlungsverbindung ·", html)

    def test_draft_cancelled_negative_and_zero(self):
        self.doc.update(docstatus=0, net_pay=-100.45, rounded_total=-100)
        self.assertIn("ENTWURF</span>", self.render())
        self.assertIn("-100.45", self.render())
        self.doc.update(docstatus=2, net_pay=0, rounded_total=0)
        self.assertIn("STORNIERT</span>", self.render())
        self.assertIn("</span>0.00", self.render())

    def test_rounding_uses_settings_and_preserves_zero(self):
        self.doc.update(net_pay=0.45, rounded_total=0)
        self.assertNotIn("Auszahlungsbetrag nach Rundung:", self.render())
        self.rounding_disabled = 0
        html = self.render()
        self.assertIn("Auszahlungsbetrag nach Rundung:", html)
        self.assertIn("CHF 0.00", html)

    def test_escape_fields_and_omit_nonpayroll_rows(self):
        self.doc.employee_name = '<script>alert("test")</script>'
        self.doc.earnings.extend([AttrDict(salary_component="Statistical", amount=1, statistical_component=1), AttrDict(salary_component="Excluded", amount=2, do_not_include_in_total=1), AttrDict(salary_component="Zero", amount=0)])
        html = self.render()
        self.assertIn("&lt;script&gt;", html)
        for value in ('<script>alert', '>Statistical<', '>Excluded<', '>Zero<'):
            self.assertNotIn(value, html)


if __name__ == "__main__":
    unittest.main()
