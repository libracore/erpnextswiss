import io
import os
import time
import zipfile
from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_last_day, getdate
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    PayrollEntry, create_salary_slips_for_employees, submit_salary_slips_for_employees)

from erpnextswiss.erpnextswiss.quellensteuer.parser import parse
from erpnextswiss.erpnextswiss.quellensteuer.tariff import import_tariffs, store
from erpnextswiss.erpnextswiss.report.quellensteuer_abrechnung.quellensteuer_abrechnung import execute as run_report

MONTHLY_RATES = {"A0N": [(0, 4), (4000, 8), (6000, 10), (8000, 12)], "B0N": [(0, 2), (4000, 4), (6000, 5), (8000, 6)], "L0N": [(0, 4.5)]}
ANNUAL_RATES = {"A0N": [(0, 4), (4000, 8), (5200, 9), (6000, 10)]}
CANTONS = {"ZZ": "Monthly", "ZX": "Monthly", "ZY": "Monthly", "YY": "Annual", "YX": "Monthly"}


def tariff_text(canton, year, created, rates):
    lines = ["00{0}{1}{2}{3}".format(canton, " " * 15, created, " " * 83)]
    for code, brackets in rates.items():
        for income_from, rate in brackets:
            lines.append("0601{0}{1:<10}{2}0101{3:09d}{4:09d} {5:02d}{6:09d}{7:05d}   ".format(
                canton, code, year, round(income_from * 100), 5000, int(code[1]), 0, round(rate * 100)))
    lines.append("1201{0}PEL       {1}0101000000100999999999 0000000000000200   ".format(canton, year))
    lines.append("1301{0}MED       {1}0101000000100999999999 0000054250000000   ".format(canton, year))
    return "\r\n".join(lines + ["99{0}{1}{2:08d}{3}".format(" " * 15, canton, len(lines) + 1, " " * 12)]) + "\r\n"


def month_range(start):
    start = getdate(start)
    return start, get_last_day(start)


class TestQuellensteuerIntegration(FrappeTestCase):
    """End-to-end checks against the database; everything is rolled back after the class."""

    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(frappe.clear_cache)
        super().setUpClass()
        cls.files = []
        for method in ("commit", "rollback"):
            patcher = patch.object(frappe.db, method)
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.addClassCleanup(lambda: [os.remove(path) for path in cls.files if os.path.exists(path)])
        cls.company = frappe.get_all("Company", pluck="name", limit=1)[0]
        cls.payable = frappe.db.get_value("Company", cls.company, "default_payroll_payable_account") or frappe.db.get_value(
            "Account", {"company": cls.company, "account_type": "Payable", "is_group": 0}, "name")
        for year in (2025, 2026):
            if not frappe.db.get_value("Fiscal Year", {"year_start_date": ("<=", f"{year}-06-30"), "year_end_date": (">=", f"{year}-06-30")}):
                frappe.get_doc({"doctype": "Fiscal Year", "year": f"QST {year}", "year_start_date": f"{year}-01-01", "year_end_date": f"{year}-12-31"}).insert()
        cls.holiday_list = frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": "_QST Integration", "from_date": "2025-01-01",
                                           "to_date": "2026-12-31"}).insert().name
        for canton, model in CANTONS.items():
            frappe.get_doc({"doctype": "QST Canton", "canton": canton, "canton_name": f"Test {canton}", "calculation_model": model,
                            "import_tariffs": 1}).insert()
        for component, abbr, component_type, qst_type in (("_QST Base", "QSTBASE", "Earning", "Periodic"), ("_QST Tax", "QSTTAX", "Deduction", None),
                                                          ("_QST Correction", "QSTCORR", "Deduction", None)):
            frappe.get_doc({"doctype": "Salary Component", "salary_component": component, "salary_component_abbr": abbr, "type": component_type,
                            "qst_type": qst_type, "depends_on_payment_days": 0}).insert()
        structure = frappe.get_doc({"doctype": "Salary Structure", "name": "_QST Integration Structure", "company": cls.company,
                                    "payroll_frequency": "Monthly", "currency": "CHF", "earnings": [
                                        {"salary_component": "_QST Base", "abbr": "QSTBASE", "amount_based_on_formula": 1, "formula": "base",
                                         "depends_on_payment_days": 0}]}).insert()
        structure.submit()
        cls.structure = structure.name
        for canton, year, created, rates in (("ZZ", 2025, "20241201", MONTHLY_RATES), ("ZZ", 2026, "20251201", MONTHLY_RATES),
                                             ("ZX", 2026, "20251201", MONTHLY_RATES), ("ZY", 2026, "20251201", MONTHLY_RATES),
                                             ("YY", 2026, "20251201", ANNUAL_RATES)):
            store(parse(tariff_text(canton, year, created, rates)), None)
        cls.settings(enabled=1, go_live_date="2025-01-01", qst_component="_QST Tax", correction_component="_QST Correction", rounding=0.05,
                     min_correction=0.05, thirteenth_frequency="Yearly", prior_year_cutoff_month=3, annual_model_correction="Monthly",
                     project_thirteenth=0)

    @staticmethod
    def settings(**values):
        doc = frappe.get_doc("QST Settings")
        doc.update(values)
        doc.save()

    def setUp(self):
        frappe.local.qst_cache = {}

    def employee(self, first_name, *records, base=5000, joining="2025-01-01", degree=None, assignments=None):
        doc = frappe.get_doc({
            "doctype": "Employee", "first_name": first_name, "gender": frappe.get_all("Gender", pluck="name", limit=1)[0],
            "date_of_birth": "1985-01-01", "date_of_joining": joining, "company": self.company, "holiday_list": self.holiday_list, "status": "Active",
            "employment_degrees": [{"date": joining, "degree": degree}] if degree else [],
            "qst_records": [{"liable": 1, "tariff_group": "A", "children": 0, **record} for record in records],
        }).insert()
        for from_date, amount in assignments or [(joining, base)]:
            frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": doc.name, "salary_structure": self.structure, "company": self.company,
                            "currency": "CHF", "from_date": from_date, "base": amount, "payroll_payable_account": self.payable}).insert().submit()
        return doc

    def slip(self, employee, start, submit=True, **values):
        frappe.local.qst_cache = {}
        start_date, end_date = month_range(start)
        doc = frappe.get_doc({"doctype": "Salary Slip", "employee": employee, "start_date": start_date, "end_date": end_date,
                              "posting_date": end_date, "payroll_frequency": "Monthly", **values})
        doc.flags.ignore_links = True
        doc.insert()
        if submit:
            frappe.local.qst_cache = {}
            doc.submit()
        return doc

    @staticmethod
    def amounts(slip):
        rows = {row.salary_component: row.amount for row in slip.deductions}
        return rows.get("_QST Tax", 0), rows.get("_QST Correction", 0)

    @staticmethod
    def details(slip):
        return [(str(row.period), row.entry_type, row.tariff_code, row.tax) for row in slip.qst_details]

    def test_tariff_import_from_zip(self):
        def run(file_name, text):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("tar26yx.txt", text)
            file_doc = frappe.get_doc({"doctype": "File", "file_name": file_name, "content": buffer.getvalue(), "is_private": 1}).insert()
            self.files.append(file_doc.get_full_path())
            imp = frappe.get_doc({"doctype": "QST Tariff Import", "file": file_doc.file_url}).insert()
            import_tariffs(imp.name)
            imp.reload()
            return imp

        text = tariff_text("YX", 2026, "20260215", MONTHLY_RATES)
        first = run("qst-test-first.zip", text)
        self.assertEqual(first.status, "Completed", first.log)
        tariff = frappe.get_doc("QST Tariff", "QST-YX-2026-20260215")
        self.assertEqual((tariff.rate_count, tariff.commission_pel, tariff.calculation_model), (9, 2, "Monthly"))
        second = run("qst-test-second.zip", text)
        self.assertEqual(second.status, "Completed")
        self.assertIn("already imported", second.log)
        conflict = run("qst-test-conflict.zip", text.replace("00800   ", "00850   ", 1))
        self.assertEqual(conflict.status, "Failed")
        self.assertIn("different data", conflict.log)
        self.assertEqual(frappe.db.count("QST Tariff", {"canton": "YX"}), 1)
        self.assertEqual(frappe.db.count("QST Tariff Rate", {"tariff": "QST-YX-2026-20260215"}), 9)
        frappe.db.delete("QST Tariff", {"canton": "YX"})
        frappe.db.delete("QST Tariff Rate", {"tariff": "QST-YX-2026-20260215"})

    def test_monthly_model_lifecycle_with_late_marriage(self):
        employee = self.employee("QST Lifecycle", {"valid_from": "2026-01-01", "canton": "ZZ"})
        for start in ("2026-01-01", "2026-02-01", "2026-03-01"):
            slip = self.slip(employee.name, start)
            self.assertEqual(self.amounts(slip), (400, 0))
            self.assertEqual(slip.net_pay, 4600)
        employee.reload()
        employee.append("qst_records", {"valid_from": "2026-02-01", "liable": 1, "canton": "ZZ", "tariff_group": "B"})
        employee.save()
        april = self.slip(employee.name, "2026-04-01")
        self.assertEqual(self.amounts(april), (200, -400))
        self.assertEqual(april.net_pay, 5200)
        self.assertEqual(self.details(april), [("2026-02-01", "Correction", "B0N", -200), ("2026-03-01", "Correction", "B0N", -200),
                                              ("2026-04-01", "Current", "B0N", 200)])

    def test_corrected_tariff_revision(self):
        employee = self.employee("QST Revision", {"valid_from": "2026-01-01", "canton": "ZX"})
        for start in ("2026-01-01", "2026-02-01"):
            self.assertEqual(self.amounts(self.slip(employee.name, start)), (400, 0))
        store(parse(tariff_text("ZX", 2026, "20260301", {**MONTHLY_RATES, "A0N": [(0, 4), (4000, 9), (6000, 10), (8000, 12)]})), None)
        march = self.slip(employee.name, "2026-03-01")
        self.assertEqual(self.amounts(march), (450, 100))
        self.assertEqual({row.qst_tariff for row in march.qst_details}, {"QST-ZX-2026-20260301"})

    def test_annual_model_salary_change(self):
        employee = self.employee("QST Annual", {"valid_from": "2026-01-01", "canton": "YY"}, assignments=[("2025-01-01", 5000), ("2026-04-01", 6000)])
        for start in ("2026-01-01", "2026-02-01", "2026-03-01"):
            self.assertEqual(self.amounts(self.slip(employee.name, start)), (400, 0))
        april = self.slip(employee.name, "2026-04-01")
        self.assertEqual(self.amounts(april), (540, 150))
        self.assertEqual(april.qst_details[-1].rate_determining_income, 69000)
        self.assertEqual({row.model for row in april.qst_details}, {"Annual"})

    def test_amended_slip_after_later_slip(self):
        employee = self.employee("QST Amended", {"valid_from": "2026-01-01", "canton": "ZZ"})
        self.slip(employee.name, "2026-01-01")
        february = self.slip(employee.name, "2026-02-01")
        self.slip(employee.name, "2026-03-01")
        employee.reload()
        employee.qst_records[0].tariff_group = "B"
        employee.save()
        february.cancel()
        amended = frappe.copy_doc(february)
        amended.update({"docstatus": 0, "amended_from": february.name})
        frappe.local.qst_cache = {}
        with patch.object(frappe, "msgprint", wraps=frappe.msgprint) as msgprint:
            amended.insert()
        self.assertEqual(self.amounts(amended), (200, 0))
        self.assertEqual([row[0] for row in self.details(amended)], ["2026-02-01"])
        self.assertTrue(any("later month" in str(call.args[0]) for call in msgprint.call_args_list))
        frappe.local.qst_cache = {}
        amended.submit()
        april = self.slip(employee.name, "2026-04-01")
        self.assertEqual(self.amounts(april), (200, -400))
        self.assertEqual([row[0] for row in self.details(april)], ["2026-01-01", "2026-03-01", "2026-04-01"])

    def test_prior_year_correction(self):
        employee = self.employee("QST Prior Year", {"valid_from": "2025-11-01", "canton": "ZZ"})
        for start in ("2025-11-01", "2025-12-01"):
            self.assertEqual(self.amounts(self.slip(employee.name, start)), (400, 0))
        employee.reload()
        employee.append("qst_records", {"valid_from": "2025-12-01", "liable": 1, "canton": "ZZ", "tariff_group": "B"})
        employee.save()
        january = self.slip(employee.name, "2026-01-01", submit=False)
        self.assertEqual(self.amounts(january), (200, -200))
        self.assertEqual(self.details(january)[0][:2], ("2025-12-01", "Correction"))
        self.settings(prior_year_cutoff_month=0)
        try:
            frappe.local.qst_cache = {}
            january.save()
            self.assertEqual(self.amounts(january), (200, 0))
        finally:
            self.settings(prior_year_cutoff_month=3)

    def test_two_slips_in_same_month(self):
        employee = self.employee("QST Two Slips", {"valid_from": "2026-01-01", "canton": "ZZ"})
        self.assertEqual(self.amounts(self.slip(employee.name, "2026-01-01")), (400, 0))
        second = self.slip(employee.name, "2026-01-01", payroll_entry="QST-TEST-OFFCYCLE")
        self.assertEqual(self.amounts(second), (800, 0))
        self.assertEqual((second.qst_details[0].taxable_income, second.qst_details[0].rate, second.qst_details[0].previously_deducted), (10000, 12, 400))

    def test_payroll_entry_batch(self):
        employees = [self.employee(f"QST Batch {index:02d}", {"valid_from": "2026-01-01", "canton": "ZY"}).name for index in range(31)]
        employees.append(self.employee("QST Batch No Tariff", {"valid_from": "2026-01-01", "canton": "YX"}).name)
        entry = frappe.get_doc({"doctype": "Payroll Entry", "company": self.company, "posting_date": "2026-01-31", "payroll_frequency": "Monthly",
                                "start_date": "2026-01-01", "end_date": "2026-01-31", "currency": "CHF", "exchange_rate": 1,
                                "payroll_payable_account": self.payable})
        entry.flags.ignore_validate = entry.flags.ignore_mandatory = True
        entry.insert()
        args = frappe._dict({"salary_slip_based_on_timesheet": 0, "payroll_frequency": "Monthly", "start_date": getdate("2026-01-01"),
                             "end_date": getdate("2026-01-31"), "company": self.company, "posting_date": getdate("2026-01-31"),
                             "deduct_tax_for_unclaimed_employee_benefits": 0, "deduct_tax_for_unsubmitted_tax_exemption_proof": 0,
                             "payroll_entry": entry.name, "exchange_rate": 1, "currency": "CHF"})
        started = time.monotonic()
        create_salary_slips_for_employees(employees, args, publish_progress=False)
        created = time.monotonic() - started
        slips = frappe.get_all("Salary Slip", filters={"payroll_entry": entry.name}, fields=["name", "employee", "docstatus"])
        self.assertEqual(len(slips), 32)
        self.assertFalse(frappe.db.get_value("Payroll Entry", entry.name, "error_message"))
        taxes = frappe.get_all("Salary Detail", filters={"parent": ("in", [s.name for s in slips]), "salary_component": "_QST Tax"}, pluck="amount")
        self.assertEqual(taxes, [400] * 31)
        started = time.monotonic()
        with patch.object(PayrollEntry, "make_accrual_jv_entry"), patch.object(PayrollEntry, "email_salary_slip"):
            submit_salary_slips_for_employees(entry, entry.get_sal_slip_list(ss_status=0), publish_progress=False)
        submitted = time.monotonic() - started
        states = {s.employee: s.docstatus for s in frappe.get_all("Salary Slip", filters={"payroll_entry": entry.name}, fields=["employee", "docstatus"])}
        self.assertEqual(sorted(states.values()), [0] + [1] * 31)
        self.assertEqual(states[employees[-1]], 0)
        print(f"\nPayroll Entry batch: 32 slips created in {created:.1f} s, submitted in {submitted:.1f} s")

    def test_report(self):
        employee = self.employee("QST Report", {"valid_from": "2026-01-01", "canton": "ZZ"})
        self.slip(employee.name, "2026-05-01")
        columns, data, message, chart, summary = run_report({"company": self.company, "canton": "ZZ", "from_date": "2026-05-01", "to_date": "2026-05-31"})
        rows = [row for row in data if row.employee == employee.name]
        self.assertEqual([(row.tariff_code, row.taxable_income, row.tax) for row in rows], [("A0N", 5000, 400)])
        total, commission, net = (item["value"] for item in summary)
        self.assertEqual(total, round(total, 2))
        self.assertAlmostEqual(commission, total * 0.02, 2)
        self.assertAlmostEqual(net, total - commission, 2)

    def test_side_job_without_degree(self):
        employee = self.employee("QST Median", {"valid_from": "2026-01-01", "canton": "ZZ", "other_employment": "Median Value (No Degree)"}, base=500)
        slip = self.slip(employee.name, "2026-01-01")
        self.assertEqual((self.amounts(slip), slip.qst_details[0].rate_determining_income, slip.qst_details[0].rate), ((40, 0), 5425, 8))

    def test_employee_validation(self):
        with self.assertRaises(frappe.ValidationError):
            self.employee("QST Invalid Date", {"valid_from": "2026-01-15", "canton": "ZZ"})
        with self.assertRaises(frappe.ValidationError):
            self.employee("QST No Degree", {"valid_from": "2026-01-01", "canton": "ZZ", "other_employment": "Extrapolate 100%"})
        with self.assertRaises(frappe.ValidationError):
            self.employee("QST Low Total", {"valid_from": "2026-01-01", "canton": "ZZ", "other_employment": "Total Degree", "total_degree": 40}, degree=60)
        employee = self.employee("QST Valid", {"valid_from": "2026-01-01", "canton": "ZZ", "tariff_group": "B", "children": 2, "church_tax": 1})
        self.assertEqual(employee.qst_records[0].tariff_code, "B2Y")

    def test_cross_border_certificate(self):
        employee = self.employee("QST Cross Border", {"valid_from": "2026-01-01", "canton": "ZZ", "tariff_group": "L", "cross_border_valid_until": "2026-01-31"})
        self.assertEqual(self.amounts(self.slip(employee.name, "2026-01-01")), (225, 0))
        february = self.slip(employee.name, "2026-02-01", submit=False)
        self.assertEqual((self.amounts(february), february.qst_details[-1].tariff_code), ((400, 0), "A0N"))

    def test_disabled_module_leaves_slip_unchanged(self):
        employee = self.employee("QST Disabled", {"valid_from": "2026-01-01", "canton": "ZZ"})
        self.settings(enabled=0)
        try:
            slip = self.slip(employee.name, "2026-06-01", submit=False)
            self.assertEqual((self.amounts(slip), len(slip.qst_details), slip.net_pay), ((0, 0), 0, 5000))
        finally:
            self.settings(enabled=1)
