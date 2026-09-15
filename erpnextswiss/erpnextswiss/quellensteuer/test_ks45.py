import unittest
from datetime import date
from unittest.mock import patch

import frappe

from erpnextswiss.erpnextswiss.quellensteuer import payroll
from erpnextswiss.erpnextswiss.quellensteuer.calculation import month_end, monthly_rdi
from erpnextswiss.erpnextswiss.quellensteuer.test_quellensteuer import SlipStub, month


def record(**values):
    return frappe._dict({"liable": 1, "canton": "ZH", "tariff_group": "A", "children": 0, "church_tax": 0, "other_employment": "None",
                         "valid_from": date(2021, 1, 1), **values})


def employee(*records, degree=None):
    return frappe._dict(name="EMP-KS45", date_of_joining=date(2010, 1, 1), relieving_date=None, qst_records=list(records),
                        employment_degrees=[frappe._dict(date=date(2021, 1, 1), degree=degree)] if degree else [])


def months_2021(periodic, aperiodic=None, thirteenth=None):
    return [month(date(2021, i + 1, 1), amount, (aperiodic or {}).get(i + 1, 0), (thirteenth or {}).get(i + 1, 0))
            for i, amount in enumerate(periodic)]


def annual_rates(table):
    return lambda tariff, code, income: table[code, round(income * 12)]


def run_ledger(test, staff, months, rates, models=None, changes=None, **settings):
    """Run months as consecutive salary slips and return (QST, correction) booked on each slip."""
    settings = frappe._dict({"enabled": 1, "go_live_date": date(2021, 1, 1), "prior_year_cutoff_month": 0, "min_correction": 0.05,
                             "rounding": 0.05, "thirteenth_frequency": "Yearly", "annual_model_correction": "Monthly",
                             "project_thirteenth": 1, "qst_component": "QST", "correction_component": "QST Correction", **settings})
    tariffs = {canton: frappe._dict(name=canton, calculation_model=model) for canton, model in (models or {"ZH": "Annual"}).items()}
    paid, booked = {}, []
    for index, current in enumerate(months):
        if changes and index in changes:
            changes[index](staff)
        slip = SlipStub(employee=staff.name, start_date=current["period"], end_date=month_end(current["period"]))
        deductions = {}
        with patch.object(frappe, "get_cached_doc", return_value=settings), patch.object(frappe, "get_doc", return_value=staff), \
                patch.object(frappe, "msgprint"), patch.object(frappe.db, "exists", return_value=None), \
                patch.object(payroll, "collect_months", return_value=({m["period"]: m for m in months[:index + 1]}, set())), \
                patch.object(payroll, "get_paid", return_value=dict(paid)), \
                patch.object(payroll, "get_tariff", side_effect=lambda canton, period: tariffs[canton]), \
                patch.object(payroll, "get_bracket", side_effect=lambda tariff, code, income: frappe._dict(rate=rates(tariff, code, income), min_tax=0)), \
                patch.object(payroll, "receives_thirteenth", return_value=True), \
                patch.object(payroll, "set_deduction", side_effect=lambda doc, component, amount: deductions.__setitem__(component, amount)):
            payroll.salary_slip_validate(slip)
        test.assertIsNone(slip.flags.qst_error, current["period"])
        for row in slip.qst_details:
            paid[row["period"]] = round(paid.get(row["period"], 0) + row["tax"], 2)
        booked.append((round(deductions["QST"], 2), round(deductions["QST Correction"], 2)))
    return booked


class TestKS45MonthlyModel(unittest.TestCase):
    def test_6_3_thirteenth_half_yearly_exit(self):
        exit_may = month(date(2021, 5, 1), 6000, thirteenth=2500, relieving=date(2021, 5, 31))
        self.assertAlmostEqual(monthly_rdi(exit_may, {"thirteenth_frequency": "Half-yearly"}), 9000)

    def test_6_4_multiple_employments(self):
        total = lambda degree: {"other_employment": "Total Degree", "total_degree": degree}
        unknown = {"other_employment": "Extrapolate 100%"}
        cases = [
            (4500, total(100), 50, 9000), (4000, total(100), 50, 8000),
            (4500, unknown, 50, 9000), (4400, unknown, 40, 11000),
            (4500, total(90), 50, 8100), (4400, total(90), 40, 9900),
            (1200, unknown, 30, 4000), (3400, unknown, 60, 5666.67), (1050, unknown, 19.23, 5460.22),
            (4500, total(70), 50, 6300), (6000, total(100), 60, 10000), (7000, {}, 100, 7000),
        ]
        for salary, values, degree, expected in cases:
            self.assertAlmostEqual(monthly_rdi(month(date(2021, 4, 1), salary), values, degree), expected, 2, (salary, values, degree))
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 4, 1), 4550, 2000), unknown, 70), 8500)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 4, 1), 4400), {"other_employment": "Other Income", "other_income": 900}), 5300)

    def test_6_5_hourly_wages(self):
        for pay, hours, expected in ((1024, 32, 5760), (1330, 38, 6300), (1485, 45, 5940), (1480, 37, 7200), (5319, 152, 6298.82),
                                     (1610, 70, 4140), (2520, 72, 6300), (6825, 195, 6300), (1750, 50, 6300)):
            self.assertAlmostEqual(monthly_rdi(month(date(2021, 3, 1), pay, hours=hours), {"hourly_wage": 1}), expected, 2, (pay, hours))
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 5, 1), 1540), {"other_employment": "Extrapolate 100%"}, 38.46), 4004.16, 2)
        self.assertAlmostEqual(monthly_rdi(month(date(2021, 7, 1), 2625, 1200, hours=75), {"hourly_wage": 1}), 7500)

    def test_6_6_entry_exit(self):
        self.assertAlmostEqual(monthly_rdi(month(date(2022, 3, 1), 3500, 6000, days=16), {}), 12562.5)

        def exit_rdi(thirteenth, frequency, relieving, joining=date(2010, 1, 1)):
            exit_month = month(relieving.replace(day=1), 3000, thirteenth=thirteenth, days=15, joining=joining, relieving=relieving)
            return monthly_rdi(exit_month, {"thirteenth_frequency": frequency})

        self.assertAlmostEqual(exit_rdi(2750, "Half-yearly", date(2021, 6, 15)), 9000)
        self.assertAlmostEqual(exit_rdi(250, "Quarterly", date(2021, 10, 15)), 7500)
        self.assertAlmostEqual(exit_rdi(2250, "Half-yearly", date(2021, 6, 15), date(2021, 2, 1)), 9000)
        self.assertAlmostEqual(exit_rdi(5750, "Yearly", date(2021, 12, 15)), 12000)
        self.assertAlmostEqual(exit_rdi(3250, "Yearly", date(2021, 10, 15), date(2021, 4, 1)), 12000)
        c_ag = month(date(2022, 3, 1), 1000, 500, 5000 / 12, days=15, relieving=date(2022, 3, 15))
        self.assertAlmostEqual(monthly_rdi(c_ag, {"thirteenth_frequency": "Yearly", "other_employment": "Total Degree", "total_degree": 90}, 40), 9500)
        self.assertAlmostEqual(monthly_rdi(month(date(2022, 3, 1), 2600), {"other_employment": "Extrapolate 100%"}, 50), 5200)


class TestKS45AnnualModel(unittest.TestCase):
    def test_7_3_1_constant_salary(self):
        booked = run_ledger(self, employee(record()), months_2021([5000] * 12), annual_rates({("A0N", 60000): 9.5}), project_thirteenth=0)
        self.assertEqual(booked, [(475, 0)] * 12)

    def test_7_3_1_thirteenth_in_december(self):
        booked = run_ledger(self, employee(record()), months_2021([5000] * 12, thirteenth={12: 5000}), annual_rates({("A0N", 65000): 10.4}))
        self.assertEqual(booked, [(520, 0)] * 11 + [(1040, 0)])

    def test_7_3_1_thirteenth_half_yearly(self):
        booked = run_ledger(self, employee(record()), months_2021([5000] * 12, thirteenth={6: 2500, 12: 2500}),
                            annual_rates({("A0N", 65000): 10.4}), thirteenth_frequency="Half-yearly")
        self.assertEqual(booked, [(520, 0)] * 5 + [(780, 0)] + [(520, 0)] * 5 + [(780, 0)])

    def test_7_3_1_salary_change(self):
        rates = annual_rates({("A0N", 60000): 9.5, ("A0N", 68000): 10.9, ("A0N", 72000): 11.5})
        booked = run_ledger(self, employee(record()), months_2021([5000] * 4 + [6000] * 6 + [8000] * 2), rates, project_thirteenth=0)
        self.assertEqual(booked, [(475, 0)] * 4 + [(654, 280)] + [(654, 0)] * 5 + [(920, 336), (920, 0)])
        self.assertEqual(sum(qst + correction for qst, correction in booked), 8280)

    def test_7_3_1_bonus(self):
        rates = annual_rates({("A0N", 65000): 10.4, ("A0N", 73000): 11.7})
        booked = run_ledger(self, employee(record()), months_2021([5000] * 12, {4: 8000}, {12: 5000}), rates)
        self.assertEqual(booked, [(520, 0)] * 3 + [(1521, 195)] + [(585, 0)] * 7 + [(1170, 0)])
        self.assertEqual(sum(qst + correction for qst, correction in booked), 8541)

    def test_7_3_2_part_time(self):
        booked = run_ledger(self, employee(record(other_employment="Extrapolate 100%"), degree=50),
                            months_2021([3000] * 12, thirteenth={12: 3000}), annual_rates({("A0N", 78000): 12.4}))
        self.assertEqual(booked, [(372, 0)] * 11 + [(744, 0)])
        booked = run_ledger(self, employee(record(other_employment="Extrapolate 100%"), degree=50),
                            months_2021([4000] * 12, thirteenth={12: 4000}), annual_rates({("A0N", 104000): 15.4}))
        self.assertEqual(booked, [(616, 0)] * 11 + [(1232, 0)])
        booked = run_ledger(self, employee(record(other_employment="Extrapolate 100%"), degree=70), months_2021([2000] * 12),
                            annual_rates({("A0N", 34286): 3.9}), project_thirteenth=0)
        self.assertEqual(booked, [(78, 0)] * 12)
        booked = run_ledger(self, employee(record(other_employment="Extrapolate 100%"), degree=20), months_2021([500] * 12),
                            annual_rates({("A0N", 30000): 3.2}), project_thirteenth=0)
        self.assertEqual(booked, [(16, 0)] * 12)

    def test_7_3_3_hourly_wage(self):
        hours = [130, 120, 125, 135, 115, 100, 140, 115, 130, 90, 120, 130]
        months = [month(date(2021, i + 1, 1), 35 * h, hours=h) for i, h in enumerate(hours)]
        booked = run_ledger(self, employee(record(hourly_wage=1)), months, annual_rates({("A0N", 75600): 12.0}))
        self.assertEqual([qst for qst, correction in booked], [546, 504, 525, 567, 483, 420, 588, 483, 546, 378, 504, 546])
        self.assertEqual(sum(qst for qst, correction in booked), 6090)

    def test_7_3_4_entry_and_exit_with_bonus(self):
        joining = date(2021, 1, 16)
        months = [month(date(2021, 1, 1), 5000, days=15, joining=joining), month(date(2021, 2, 1), 6000, days=20, joining=joining),
                  month(date(2021, 3, 1), 3000, 2000, days=18, joining=joining)]
        rates = annual_rates({("A0N", 120000): 16.9, ("A0N", 113143): 16.3, ("A0N", 97094): 14.6})
        booked = run_ledger(self, employee(record()), months, rates, project_thirteenth=0)
        self.assertEqual(booked, [(845, 0), (978, -30), (730, -187)])


class TestKS45PersonalChanges(unittest.TestCase):
    def test_7_4_1_marriage(self):
        rates = annual_rates({("A0N", 65000): 10.4, ("B0N", 65000): 5.0})
        months = months_2021([5000] * 12, thirteenth={12: 5000})
        booked = run_ledger(self, employee(record(), record(valid_from=date(2021, 6, 1), tariff_group="B")), months, rates)
        self.assertEqual(booked, [(520, 0)] * 5 + [(250, 0)] * 6 + [(500, 0)])
        self.assertEqual(sum(qst for qst, correction in booked), 4600)

    def test_7_4_1_marriage_reported_late(self):
        rates = annual_rates({("A0N", 65000): 10.4, ("B0N", 65000): 5.0})
        changes = {7: lambda staff: staff.qst_records.append(record(valid_from=date(2021, 6, 1), tariff_group="B"))}
        booked = run_ledger(self, employee(record()), months_2021([5000] * 12, thirteenth={12: 5000}), rates, changes=changes)
        self.assertEqual(booked, [(520, 0)] * 7 + [(250, -540)] + [(250, 0)] * 3 + [(500, 0)])

    def test_7_4_4_marriage_child_and_bonus(self):
        rates = annual_rates({("A0N", 65000): 10.4, ("A0N", 95000): 14.4, ("B0N", 95000): 9.3, ("B1N", 95000): 6.4})
        staff = employee(record(), record(valid_from=date(2021, 6, 1), tariff_group="B"), record(valid_from=date(2021, 11, 1), tariff_group="B", children=1))
        booked = run_ledger(self, staff, months_2021([5000] * 12, {2: 30000}, {12: 5000}), rates)
        self.assertEqual(booked, [(520, 0), (5040, 200)] + [(720, 0)] * 3 + [(465, 0)] * 5 + [(320, 0), (640, 0)])
        self.assertEqual(sum(qst + correction for qst, correction in booked), 11205)

    def test_7_4_5_spouse_starts_working(self):
        rates = annual_rates({("B0N", 52000): 3.0, ("C0N", 52000): 7.2})
        staff = employee(record(tariff_group="B"), record(valid_from=date(2021, 10, 1), tariff_group="C"))
        booked = run_ledger(self, staff, months_2021([4000] * 12, thirteenth={12: 4000}), rates)
        self.assertEqual(booked, [(120, 0)] * 9 + [(288, 0)] * 2 + [(576, 0)])
        self.assertEqual(sum(qst for qst, correction in booked), 2232)

    def test_7_4_6_birth_and_spouse_stops_working(self):
        rates = lambda tariff, code, income: {"C0N": 12.0 if round(income * 12) < 79000 else 12.1, "C1N": 9.8, "B1N": 4.1}[code]
        staff = employee(record(tariff_group="C"), record(valid_from=date(2021, 9, 1), tariff_group="C", children=1),
                         record(valid_from=date(2021, 11, 1), tariff_group="B", children=1))
        booked = run_ledger(self, staff, months_2021([6000] * 7 + [6200] * 5, thirteenth={12: 6000}), rates)
        self.assertEqual(booked, [(720, 0)] * 7 + [(750.2, 42), (607.6, 0), (607.6, 0), (254.2, 0), (500.2, 0)])
        self.assertAlmostEqual(sum(qst + correction for qst, correction in booked), 7801.8)

    def test_7_4_7_salary_change_and_spouse_starts_working(self):
        rates = annual_rates({("B0N", 96000): 9.4, ("B0N", 114000): 11.7, ("C0N", 114000): 15.3})
        staff = employee(record(tariff_group="B"), record(valid_from=date(2021, 10, 1), tariff_group="C"))
        booked = run_ledger(self, staff, months_2021([8000] * 6 + [11000] * 6), rates, project_thirteenth=0)
        self.assertEqual(booked, [(752, 0)] * 6 + [(1287, 1104), (1287, 0), (1287, 0)] + [(1683, 0)] * 3)
        self.assertEqual(sum(qst + correction for qst, correction in booked), 14526)

    def test_7_4_8_marriage_and_salary_change(self):
        rates = annual_rates({("A0N", 72000): 11.5, ("A0N", 80000): 12.7, ("C0N", 72000): 11.3, ("C0N", 80000): 12.3})
        staff = employee(record(), record(valid_from=date(2021, 5, 1), tariff_group="C"))
        booked = run_ledger(self, staff, months_2021([6000] * 8 + [8000] * 4), rates, project_thirteenth=0)
        self.assertEqual(booked, [(690, 0)] * 4 + [(678, 0)] * 4 + [(984, 528)] + [(984, 0)] * 3)
        self.assertEqual(sum(qst + correction for qst, correction in booked), 9936)


class TestKS45CantonChange(unittest.TestCase):
    def canton_rates(self, table, annual):
        return lambda tariff, code, income: table[tariff, round(income * 12) if tariff in annual else round(income)]

    def test_8_2_annual_to_monthly(self):
        rates = self.canton_rates({("TI", 65000): 10.4, ("TI", 95000): 14.4, ("BE", 5000): 10.63, ("BE", 10000): 17.01}, ("TI",))
        staff = employee(record(canton="TI"), record(valid_from=date(2021, 9, 1), canton="BE"))
        booked = run_ledger(self, staff, months_2021([5000] * 12, {2: 30000}, {12: 5000}), rates, models={"TI": "Annual", "BE": "Monthly"})
        self.assertEqual(booked, [(520, 0), (5040, 200)] + [(720, 0)] * 6 + [(531.5, 0)] * 3 + [(1701, 0)])
        self.assertAlmostEqual(sum(qst + correction for qst, correction in booked), 13375.5)

    def test_8_3_monthly_to_annual(self):
        rates = self.canton_rates({("BE", 5000): 10.63, ("BE", 35000): 30.76, ("TI", 65000): 10.4}, ("TI",))
        staff = employee(record(canton="BE"), record(valid_from=date(2021, 9, 1), canton="TI"))
        booked = run_ledger(self, staff, months_2021([5000] * 12, {2: 30000}, {12: 5000}), rates, models={"BE": "Monthly", "TI": "Annual"})
        self.assertEqual(booked, [(531.5, 0), (10766, 0)] + [(531.5, 0)] * 6 + [(520, 0)] * 3 + [(1040, 0)])
        self.assertAlmostEqual(sum(qst + correction for qst, correction in booked), 17086.5)

    def test_8_4_annual_to_annual(self):
        rates = self.canton_rates({("TI", 65000): 10.4, ("TI", 95000): 14.4, ("GE", 65000): 11.31}, ("TI", "GE"))
        staff = employee(record(canton="TI"), record(valid_from=date(2021, 9, 1), canton="GE"))
        booked = run_ledger(self, staff, months_2021([5000] * 12, {2: 30000}, {12: 5000}), rates, models={"TI": "Annual", "GE": "Annual"})
        self.assertEqual(booked, [(520, 0), (5040, 200)] + [(720, 0)] * 6 + [(565.5, 0)] * 3 + [(1131, 0)])
        self.assertAlmostEqual(sum(qst + correction for qst, correction in booked), 12907.5)
