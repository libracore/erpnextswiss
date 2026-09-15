import unittest
from datetime import date
from unittest.mock import patch

import frappe

from erpnextswiss.erpnextswiss.quellensteuer import payroll
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


def month(period, periodic=0, aperiodic=0, thirteenth=0, days=30, hours=0, joining=date(2010, 1, 1), relieving=None):
    return {"period": period, "periodic": periodic, "aperiodic": aperiodic, "thirteenth": thirteenth, "days": days,
            "hours": hours, "joining": joining, "relieving": relieving}


class TestParser(unittest.TestCase):
    def test_parse(self):
        data = parse(tariff_file([rate_line("A0N", 1, 0), rate_line("A0N", 3101, 7.15), rate_line("R0N", 1, 3),
                                  "1201ZZPEL       20260101000000100999999999 0000000000000200   ",
                                  "1301ZZMED       20260101000000100999999999 0000058750000000   "]))
        self.assertEqual((data["canton"], data["creation_date"], data["valid_from"]), ("ZZ", date(2025, 12, 1), date(2026, 1, 1)))
        self.assertEqual([row["code"] for row in data["rows"]], ["A0N", "A0N"])
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

    def test_tax_and_code(self):
        self.assertEqual(tax_amount(5000, 10.9), 545)
        self.assertEqual(tax_amount(100, 1, 20), 20)
        self.assertEqual(tax_amount(1234.56, 10), 123.45)
        self.assertEqual((tariff_code("B", 2, True), tariff_code("G", 3, True), tariff_code("A", 12)), ("B2Y", "G9N", "A9N"))


class TestPayroll(unittest.TestCase):
    settings = frappe._dict(rounding=0.05, thirteenth_frequency="Yearly")

    def employee(self, *records):
        return frappe._dict(date_of_joining=date(2010, 1, 1), relieving_date=None, employment_degrees=[],
                            qst_records=[frappe._dict({"liable": 1, "canton": "ZZ", "tariff_group": "A", "children": 0, "church_tax": 0,
                                                       "other_employment": "None", **record}) for record in records])

    def run_calculation(self, employee, salaries, model, rates):
        tariff = frappe._dict(name="QST-ZZ-2021-20201201", calculation_model=model)
        months = {date(2021, i + 1, 1): month(date(2021, i + 1, 1), salary) for i, salary in enumerate(salaries)}
        with patch.object(payroll, "get_tariff", return_value=tariff), \
                patch.object(payroll, "get_bracket", side_effect=lambda t, code, income: rates(code, income)):
            return payroll.calculate(employee, months, max(months), self.settings)

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
