import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils.synchronization import filelock

from erpnextswiss.erpnextswiss.quellensteuer import payroll, tariff
from erpnextswiss.erpnextswiss.quellensteuer.calculation import (
    annual_rdi, days_30, month_end, monthly_rdi, tariff_code, tax_amount, thirteenth_rdi)
from erpnextswiss.erpnextswiss.quellensteuer.parser import TariffFileError, parse


def rate_line(code, income_from, rate, record_type="06", transaction="01", min_tax=0):
    return "{0}{1}ZZ{2:<10}20260101{3:09d}{4:09d} {5:02d}{6:09d}{7:05d}   ".format(
        record_type, transaction, code, int(income_from * 100), 5000, int(code[1]) if code[1].isdigit() else 0,
        int(min_tax * 100), int(rate * 100))


def tariff_file(lines):
    lines = ["00ZZ" + " " * 15 + "20251201" + " " * 83] + lines
    return "\r\n".join(lines + ["99" + " " * 15 + "ZZ{0:08d}".format(len(lines) + 1) + " " * 12]) + "\r\n"


def month(period, periodic=0, aperiodic=0, thirteenth=0, days=30, hours=0, joining=date(2010, 1, 1), relieving=None, replacement=0):
    return {"period": period, "periodic": periodic, "aperiodic": aperiodic, "thirteenth": thirteenth, "replacement": replacement,
            "days": days, "hours": hours, "joining": joining, "relieving": relieving}


class TestParser(unittest.TestCase):
    def test_parse(self):
        data = parse(tariff_file([rate_line("A0N", 1, 0), rate_line("A0N", 3101, 7.15), rate_line("R0N", 1, 3),
                                  "1201ZZPEL       20260101000000100999999999 0000000000000200   ",
                                  "1301ZZMED       20260101000000100999999999 0000058750000000   "]))
        self.assertEqual((data["canton"], data["creation_date"], data["valid_from"]), ("ZZ", date(2025, 12, 1), date(2026, 1, 1)))
        self.assertEqual([row["code"] for row in data["rows"]], ["A0N", "A0N", "R0N"])
        self.assertEqual((data["rows"][1]["income_from"], data["rows"][1]["step"], data["rows"][1]["rate"]), (3101, 50, 7.15))
        self.assertEqual((data["commission"]["PEL"], data["median_value"]), (2, 5875))

    def test_hash_ignores_order(self):
        lines = [rate_line("A0N", 1, 0), rate_line("A0N", 3101, 7.15)]
        self.assertEqual(parse(tariff_file(lines))["content_hash"], parse(tariff_file(lines[::-1]))["content_hash"])
        self.assertNotEqual(parse(tariff_file(lines))["content_hash"], parse(tariff_file([lines[0], rate_line("A0N", 3101, 7.2)]))["content_hash"])

    def test_invalid_files(self):
        with self.assertRaises(TariffFileError):
            parse(tariff_file([rate_line("A0N", 1, 0)]).replace("ZZ00000003", "ZZ00000004"))
        with self.assertRaises(TariffFileError):
            parse(tariff_file([rate_line("A0N", 1, 0, transaction="02")]))


class TestTariffImport(unittest.TestCase):
    def test_start_refused_while_import_running(self):
        doc = MagicMock()
        with patch.object(frappe, "get_doc", return_value=doc), patch.object(tariff, "is_job_enqueued", return_value=True), \
                patch.object(frappe, "enqueue") as enqueue:
            with self.assertRaises(frappe.ValidationError):
                tariff.start_import("QST-IMP-TEST")
        enqueue.assert_not_called()
        doc.db_set.assert_not_called()

    def test_import_fails_while_locked(self):
        doc = MagicMock(file="/private/files/tar26zz.zip")
        with patch.object(frappe, "get_doc", return_value=doc), patch.object(tariff, "run_import") as run_import, \
                patch.object(frappe.db, "rollback"), patch.object(frappe.db, "commit"), patch.object(frappe, "log_error"), \
                filelock(tariff.IMPORT_JOB):
            tariff.import_tariffs("QST-IMP-TEST")
        run_import.assert_not_called()
        self.assertEqual(doc.db_set.call_args[0][0]["status"], "Failed")


class TestCalculation(unittest.TestCase):
    def test_days_30(self):
        cases = {date(2023, 3, 31): (1, 30), date(2023, 3, 30): (1, 30), date(2023, 3, 29): (2, 29), date(2024, 2, 29): (1, 30),
                 date(2024, 2, 28): (1, 30), date(2023, 2, 28): (1, 30), date(2023, 2, 27): (4, 27)}
        for day, (entry_days, exit_days) in cases.items():
            start, end = day.replace(day=1), month_end(day)
            self.assertEqual(days_30(start, end, joining=day), entry_days, day)
            self.assertEqual(days_30(start, end, relieving=day), exit_days, day)
        self.assertEqual(days_30(date(2022, 3, 1), date(2022, 3, 31), relieving=date(2022, 3, 16)), 16)

    def test_thirteenth(self):
        self.assertAlmostEqual(thirteenth_rdi(2750, "Half-yearly", date(2021, 6, 30), relieving=date(2021, 6, 15)), 3000)
        self.assertAlmostEqual(thirteenth_rdi(250, "Quarterly", date(2021, 10, 31), relieving=date(2021, 10, 15)), 1500)
        self.assertAlmostEqual(thirteenth_rdi(5750, "Yearly", date(2021, 12, 31), relieving=date(2021, 12, 15)), 6000)
        self.assertAlmostEqual(thirteenth_rdi(2250, "Half-yearly", date(2021, 6, 30), date(2021, 2, 1), date(2021, 6, 15)), 3000)
        self.assertAlmostEqual(thirteenth_rdi(3250, "Yearly", date(2021, 10, 31), date(2021, 4, 1), date(2021, 10, 15)), 6000)
        self.assertAlmostEqual(thirteenth_rdi(6000, "Yearly", date(2021, 11, 30)), 6000)
        self.assertAlmostEqual(thirteenth_rdi(3000, "Half-yearly", date(2021, 5, 31), date(2021, 1, 1)), 3000)
        self.assertAlmostEqual(thirteenth_rdi(3000, "Yearly", date(2021, 11, 30), date(2021, 7, 1)), 6000)

    def test_monthly_rdi(self):
        self.assertAlmostEqual(monthly_rdi(month(date(2022, 3, 1), 3500, 6000, days=16), {}), 12562.5)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 6, 1), 3000, thirteenth=2750, days=15, relieving=date(2021, 6, 15)),
                                           {"thirteenth_frequency": "Half-yearly"}), 9000)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 4, 1), 4500), {"other_employment": "Total Degree", "total_degree": 90}, 50), 8100)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 4, 1), 4500), {"other_employment": "Extrapolate 100%"}, 50), 9000)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 4, 1), 4400), {"other_employment": "Other Income", "other_income": 900}, 80), 5300)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 6, 1), 2520, hours=72, days=12), {"hourly_wage": 1}), 6300)
        exit_40 = month(date(2022, 3, 1), 1000, 500, thirteenth=5000 / 12, days=15, relieving=date(2022, 3, 15))
        self.assertAlmostEqual(monthly_rdi(exit_40, {"thirteenth_frequency": "Yearly", "other_employment": "Total Degree", "total_degree": 90}, 40), 9500)

    def test_annual_rdi(self):
        salaries = [5000] * 4 + [6000] * 6 + [8000]
        months = [month(date(2021, i + 1, 1), salary) for i, salary in enumerate(salaries)]
        self.assertAlmostEqual(annual_rdi(months[:5], {}, full_year=True), 68000)
        self.assertAlmostEqual(annual_rdi(months, {}, full_year=True), 72000)
        partial = [month(date(2021, 1, 1), 5000, days=15), month(date(2021, 2, 1), 6000, days=20), month(date(2021, 3, 1), 3000, 2000, days=18)]
        self.assertAlmostEqual(annual_rdi(partial[:2], {}), 113142.857, 2)
        self.assertAlmostEqual(annual_rdi(partial, {}), 97094.34, 2)
        self.assertAlmostEqual(annual_rdi([month(date(2021, 1, 1), 4550, hours=130)], {"hourly_wage": 1}), 75600)
        self.assertAlmostEqual(annual_rdi([month(date(2021, 1, 1), 2000)], {"other_employment": "Extrapolate 100%"}, 70, True), 34285.71, 2)

    def test_annual_rdi_thirteenth_scaled(self):
        year = [month(date(2021, m, 1), 3000, thirteenth=3000 if m == 12 else 0) for m in range(1, 13)]
        self.assertAlmostEqual(annual_rdi(year, {"other_employment": "Extrapolate 100%"}, 50, True), 78000)

    def test_annual_rdi_projected_thirteenth(self):
        yearly, half = {"thirteenth_frequency": "Yearly"}, {"thirteenth_frequency": "Half-yearly"}
        self.assertAlmostEqual(annual_rdi([month(date(2021, 1, 1), 5000)], yearly, full_year=True, project_thirteenth=True), 65000)
        december = [month(date(2021, m, 1), 5000, thirteenth=5000 if m == 12 else 0) for m in range(1, 13)]
        self.assertAlmostEqual(annual_rdi(december, yearly, full_year=True, project_thirteenth=True), 65000)
        june = [month(date(2021, m, 1), 5000, thirteenth=2500 if m == 6 else 0) for m in range(1, 7)]
        self.assertAlmostEqual(annual_rdi(june[:5], half, full_year=True, project_thirteenth=True), 65000)
        self.assertAlmostEqual(annual_rdi(june, half, full_year=True, project_thirteenth=True), 65000)
        self.assertAlmostEqual(annual_rdi(june, half, full_year=True), 62500)

    def test_tax_and_code(self):
        self.assertEqual(tax_amount(5000, 10.9), 545)
        self.assertEqual(tax_amount(100, 1, 20), 20)
        self.assertEqual(tax_amount(1234.56, 10), 123.45)
        self.assertEqual((tariff_code("B", 2, True), tariff_code("G", 3, True), tariff_code("A", 12)), ("B2Y", "G9N", "A9N"))
        self.assertEqual((tariff_code("L", 1, True), tariff_code("V", 2), tariff_code("SF", 2, True)), ("L1Y", "V9N", "SFN"))


class SlipStub(frappe._dict):
    def __init__(self, **kwargs):
        super().__init__(flags=frappe._dict(), qst_details=[], **kwargs)

    def set(self, key, value):
        self[key] = value

    def set_net_pay(self):
        pass

    compute_year_to_date = compute_month_to_date = compute_component_wise_year_to_date = set_net_pay


class TestPayroll(unittest.TestCase):
    settings = frappe._dict(rounding=0.05, thirteenth_frequency="Yearly")

    def employee(self, *records):
        return frappe._dict(date_of_joining=date(2010, 1, 1), relieving_date=None, employment_degrees=[],
                            qst_records=[frappe._dict({"liable": 1, "canton": "ZZ", "tariff_group": "A", "children": 0, "church_tax": 0,
                                                       "other_employment": "None", **record}) for record in records])

    def run_calculation(self, employee, salaries, model, rates, settings=None):
        tariff = frappe._dict(name="QST-ZZ-2021-20201201", calculation_model=model)
        months = {date(2021, i + 1, 1): month(date(2021, i + 1, 1), salary) for i, salary in enumerate(salaries)}
        with patch.object(payroll, "get_tariff", return_value=tariff), \
                patch.object(payroll, "get_bracket", side_effect=lambda t, code, income: rates(code, income)):
            return payroll.calculate(employee, months, max(months), settings or self.settings)

    def validate_slip(self, employee, salaries, paid, tariffs, go_live=date(2021, 1, 1), later_slip=None):
        settings = frappe._dict(self.settings, enabled=1, go_live_date=go_live, prior_year_cutoff_month=0, min_correction=0.05,
                                qst_component="QST", correction_component="QST Correction", annual_model_correction="Monthly")
        months = {date(2021, i + 1, 1): month(date(2021, i + 1, 1), salary) for i, salary in enumerate(salaries)}
        slip = SlipStub(employee="EMP-TEST", start_date=max(months), end_date=month_end(max(months)))
        deductions = {}
        with patch.object(frappe, "get_cached_doc", return_value=settings), patch.object(frappe, "get_doc", return_value=employee), \
                patch.object(frappe, "msgprint") as msgprint, patch.object(frappe.db, "exists", return_value=later_slip), \
                patch.object(payroll, "collect_months", return_value=(months, set())), \
                patch.object(payroll, "get_paid", return_value=paid), \
                patch.object(payroll, "get_tariff", side_effect=lambda canton, period: tariffs.get(period)), \
                patch.object(payroll, "get_bracket", return_value=frappe._dict(rate=10.4, min_tax=0)), \
                patch.object(payroll, "set_deduction", side_effect=lambda doc, component, amount: deductions.__setitem__(component, amount)):
            payroll.salary_slip_validate(slip)
        slip.messages = msgprint.call_args_list
        return slip, deductions

    def test_later_slip_skips_corrections_with_message(self):
        employee = self.employee({"valid_from": date(2021, 1, 1)})
        tariff = frappe._dict(name="QST-ZZ-2021-20201201", calculation_model="Monthly")
        tariffs = {date(2021, m, 1): tariff for m in (1, 2, 3)}
        paid = {date(2021, 1, 1): 500, date(2021, 2, 1): 520}
        slip, deductions = self.validate_slip(employee, [5000] * 3, paid, tariffs, later_slip="Sal Slip/EMP-TEST/00004")
        self.assertEqual((deductions["QST"], deductions["QST Correction"]), (520, 0))
        self.assertEqual([row["period"] for row in slip.qst_details], [date(2021, 3, 1)])
        self.assertEqual(len(slip.messages), 1)
        self.assertIn("later month", slip.messages[0].args[0])
        self.assertEqual(slip.messages[0].kwargs["indicator"], "orange")
        slip, deductions = self.validate_slip(employee, [5000] * 3, paid, tariffs)
        self.assertEqual((deductions["QST"], deductions["QST Correction"]), (520, 20))
        self.assertEqual(slip.messages, [])

    def test_validate_blocks_missing_degree_in_current_month(self):
        employee = self.employee({"valid_from": date(2021, 1, 1), "other_employment": "Extrapolate 100%"})
        tariff = frappe._dict(name="QST-ZZ-2021-20201201", calculation_model="Monthly")
        slip, deductions = self.validate_slip(employee, [4500], {}, {date(2021, 1, 1): tariff})
        self.assertIn("employment degree", slip.flags.qst_error)
        self.assertEqual(deductions["QST"], 0)
        with self.assertRaises(frappe.ValidationError):
            payroll.salary_slip_before_submit(slip)

    def test_validate_blocks_missing_tariff_in_earlier_month(self):
        employee = self.employee({"valid_from": date(2021, 1, 1)})
        tariff = frappe._dict(name="QST-ZZ-2021-20201201", calculation_model="Monthly")
        tariffs = {date(2021, 1, 1): tariff, date(2021, 3, 1): tariff}
        paid = {date(2021, 1, 1): 520, date(2021, 2, 1): 520}
        slip, deductions = self.validate_slip(employee, [5000] * 3, paid, tariffs)
        self.assertIn("tariff", slip.flags.qst_error)
        self.assertEqual((deductions["QST"], deductions["QST Correction"]), (520, 0))
        self.assertEqual([row["period"] for row in slip.qst_details], [date(2021, 3, 1)])
        with self.assertRaises(frappe.ValidationError):
            payroll.salary_slip_before_submit(slip)
        slip, deductions = self.validate_slip(employee, [5000] * 3, paid, tariffs, go_live=date(2021, 3, 1))
        self.assertIsNone(slip.flags.qst_error)
        self.assertEqual((deductions["QST"], deductions["QST Correction"]), (520, 0))

    def calculate_move(self, records, models, current, settings, extra=None):
        employee = self.employee(*records)
        months = {date(2021, m, 1): month(date(2021, m, 1), 5000) for m in range(1, current.month + 1)}
        for period, values in (extra or {}).items():
            months[period].update(values)
        tariffs = {canton: frappe._dict(name=f"QST-{canton}-2021-20201201", calculation_model=model) for canton, model in models.items()}
        with patch.object(payroll, "get_tariff", side_effect=lambda canton, period: tariffs[canton]), \
                patch.object(payroll, "get_bracket", return_value=frappe._dict(rate=10, min_tax=0)), \
                patch.object(payroll, "receives_thirteenth", return_value=True):
            return payroll.calculate(employee, months, current, settings)

    def test_canton_change_annual_to_annual(self):
        records = ({"valid_from": date(2021, 1, 1), "canton": "TI"}, {"valid_from": date(2021, 9, 1), "canton": "GE"})
        extra = {date(2021, 2, 1): {"aperiodic": 30000}, date(2021, 12, 1): {"thirteenth": 5000}}
        results = self.calculate_move(records, {"TI": "Annual", "GE": "Annual"}, date(2021, 12, 1), frappe._dict(self.settings, project_thirteenth=1), extra)
        self.assertEqual([round(results[date(2021, m, 1)]["rdi"]) for m in (3, 9, 12)], [95000, 65000, 65000])
        results = self.calculate_move(records, {"TI": "Annual", "GE": "Annual"}, date(2021, 9, 1), self.settings)
        self.assertAlmostEqual(results[date(2021, 9, 1)]["rdi"], 60000)

    def test_canton_change_monthly_to_annual(self):
        records = ({"valid_from": date(2021, 1, 1), "canton": "BE"}, {"valid_from": date(2021, 9, 1), "canton": "TI"})
        extra = {date(2021, 2, 1): {"aperiodic": 30000}}
        results = self.calculate_move(records, {"BE": "Monthly", "TI": "Annual"}, date(2021, 9, 1), frappe._dict(self.settings, project_thirteenth=1), extra)
        self.assertEqual([round(results[date(2021, m, 1)]["rdi"]) for m in (2, 9)], [35000, 65000])
        self.assertEqual((results[date(2021, 2, 1)]["model"], results[date(2021, 9, 1)]["model"]), ("Monthly", "Annual"))

    def test_cross_border_certificate(self):
        rates = lambda code, income: frappe._dict(rate={"L0N": 4.5, "A0N": 10.4, "SFN": 0}[code], min_tax=0)
        with_certificate = self.employee({"valid_from": date(2021, 1, 1), "tariff_group": "L", "cross_border_valid_until": date(2021, 12, 31)})
        results = self.run_calculation(with_certificate, [5000], "Monthly", rates)
        self.assertEqual((results[date(2021, 1, 1)]["code"], results[date(2021, 1, 1)]["tax"], results[date(2021, 1, 1)]["fallback"]), ("L0N", 225, False))
        expired = self.employee({"valid_from": date(2021, 1, 1), "tariff_group": "L", "cross_border_valid_until": date(2020, 12, 31)})
        results = self.run_calculation(expired, [5000], "Monthly", rates)
        self.assertEqual((results[date(2021, 1, 1)]["code"], results[date(2021, 1, 1)]["tax"], results[date(2021, 1, 1)]["fallback"]), ("A0N", 520, True))
        france = self.employee({"valid_from": date(2021, 1, 1), "tariff_group": "SF", "cross_border_valid_until": date(2021, 12, 31)})
        results = self.run_calculation(france, [5000], "Monthly", rates)
        self.assertEqual((results[date(2021, 1, 1)]["code"], results[date(2021, 1, 1)]["tax"]), ("SFN", 0))

    def test_validate_shows_cross_border_fallback(self):
        employee = self.employee({"valid_from": date(2021, 1, 1), "tariff_group": "M"})
        tariff = frappe._dict(name="QST-ZZ-2021-20201201", calculation_model="Monthly")
        slip, deductions = self.validate_slip(employee, [5000], {}, {date(2021, 1, 1): tariff})
        self.assertEqual((slip.qst_details[0]["tariff_code"], slip.qst_details[0]["reason"]), ("B0N", "No cross-border certificate"))
        self.assertEqual(len(slip.messages), 1)
        self.assertIn("ordinary tariff B0N", slip.messages[0].args[0])

    def test_degree_required(self):
        rates = lambda code, income: frappe._dict(rate=10, min_tax=0)
        employee = self.employee({"valid_from": date(2021, 1, 1), "other_employment": "Extrapolate 100%"})
        result = self.run_calculation(employee, [4500], "Monthly", rates)[date(2021, 1, 1)]
        self.assertTrue(result["error"])
        employee.employment_degrees = [frappe._dict(date=date(2021, 1, 1), degree=50)]
        result = self.run_calculation(employee, [4500], "Monthly", rates)[date(2021, 1, 1)]
        self.assertEqual((result["error"], result["rdi"]), (None, 9000))

    def test_median_value_required(self):
        employee = self.employee({"valid_from": date(2021, 1, 1), "other_employment": "Median Value (No Degree)"})
        result = self.run_calculation(employee, [500], "Monthly", lambda code, income: frappe._dict(rate=10, min_tax=0))[date(2021, 1, 1)]
        self.assertIn("median value", result["error"])

    def test_annual_model_projects_thirteenth(self):
        employee = self.employee({"valid_from": date(2021, 1, 1)})
        rates = lambda code, income: frappe._dict(rate=10.4, min_tax=0)
        settings = frappe._dict(self.settings, project_thirteenth=1)
        with patch.object(payroll, "receives_thirteenth", return_value=True):
            results = self.run_calculation(employee, [5000], "Annual", rates, settings)
        self.assertAlmostEqual(results[date(2021, 1, 1)]["rdi"], 65000)
        self.assertEqual(results[date(2021, 1, 1)]["tax"], 520)
        with patch.object(payroll, "receives_thirteenth", return_value=False):
            results = self.run_calculation(employee, [5000], "Annual", rates, settings)
        self.assertAlmostEqual(results[date(2021, 1, 1)]["rdi"], 60000)

    def test_annual_model_recalculates_year(self):
        rates = lambda code, income: frappe._dict(rate={5000: 9.5, 5667: 10.9, 6000: 11.5}[round(income)], min_tax=0)
        employee = self.employee({"valid_from": date(2021, 1, 1)})
        results = self.run_calculation(employee, [5000] * 4 + [6000] * 6 + [8000], "Annual", rates)
        self.assertEqual([results[date(2021, m, 1)]["tax"] for m in (1, 5, 11)], [575, 690, 920])
        results = self.run_calculation(employee, [5000] * 4 + [6000], "Annual", rates)
        self.assertEqual([results[date(2021, m, 1)]["tax"] for m in (1, 5)], [545, 654])

    def test_monthly_model_tariff_change(self):
        rates = lambda code, income: frappe._dict(rate={"A0N": 10.4, "B0N": 5.0}[code], min_tax=0)
        employee = self.employee({"valid_from": date(2021, 1, 1)}, {"valid_from": date(2021, 6, 1), "tariff_group": "B"})
        results = self.run_calculation(employee, [5000] * 6, "Monthly", rates)
        self.assertEqual([results[date(2021, m, 1)]["tax"] for m in (5, 6)], [520, 250])
        self.assertEqual(results[date(2021, 6, 1)]["code"], "B0N")

    def test_not_liable_and_fixed(self):
        employee = self.employee({"valid_from": date(2021, 1, 1), "other_employment": "Fixed Rate", "fixed_rate": 5},
                                 {"valid_from": date(2021, 3, 1), "liable": 0})
        results = self.run_calculation(employee, [5000] * 3, "Monthly", lambda code, income: None)
        self.assertEqual([results[date(2021, m, 1)]["tax"] for m in (1, 3)], [250, 0])
