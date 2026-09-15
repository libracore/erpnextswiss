from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from erpnextswiss.erpnextswiss.quellensteuer.calculation import (
    annual_rdi, days_30, month_end, monthly_rdi, tariff_code, tax_amount)
from erpnextswiss.erpnextswiss.quellensteuer.tariff import cache, get_bracket, get_tariff

TYPE_KEYS = {"Periodic": "periodic", "Aperiodic": "aperiodic", "13th Salary": "thirteenth"}
SUM_KEYS = ("periodic", "aperiodic", "thirteenth", "hours")


def salary_slip_validate(doc, method=None):
    """Calculate Quellensteuer and corrections of earlier months on a salary slip."""
    settings = frappe.get_cached_doc("QST Settings")
    if not settings.enabled or doc.get("qst_skip"):
        return
    doc.flags.qst_error = None
    period = getdate(doc.start_date).replace(day=1)
    scope_start = date(period.year - (1 if period.month <= cint(settings.prior_year_cutoff_month) else 0), 1, 1)
    employee = frappe.get_doc("Employee", doc.employee)
    months, skipped = collect_months(doc, employee, scope_start, period)
    paid = get_paid(doc, scope_start)
    locked = skipped | {p for p in months if p < getdate(settings.go_live_date)}
    if frappe.db.exists("Salary Slip", {"employee": doc.employee, "docstatus": 1, "start_date": (">", month_end(period))}):
        locked |= set(months)
    details, current, correction = [], 0, 0
    for month_period, result in sorted(calculate(employee, months, period, settings).items()):
        delta = flt(result["tax"] - paid.get(month_period, 0), 2)
        if month_period == period:
            current = delta
            if result["error"]:
                doc.flags.qst_error = result["error"]
                frappe.msgprint(result["error"], title=_("Quellensteuer"), indicator="red")
        elif (month_period in locked or abs(delta) < flt(settings.min_correction)
              or not correction_allowed(result, doc, employee, settings)):
            continue
        else:
            correction += delta
        if month_period == period and not (result["record"] or delta):
            continue
        details.append(detail_row(result, months[month_period], month_period, paid.get(month_period, 0), delta,
                                  "Current" if month_period == period else "Correction"))
    doc.set("qst_details", details)
    set_deduction(doc, settings.qst_component, current)
    set_deduction(doc, settings.correction_component, flt(correction, 2))
    doc.set_net_pay()
    doc.compute_year_to_date()
    doc.compute_month_to_date()
    doc.compute_component_wise_year_to_date()


def salary_slip_before_submit(doc, method=None):
    if doc.flags.qst_error:
        frappe.throw(doc.flags.qst_error, title=_("Quellensteuer"))


def collect_months(doc, employee, scope_start, period):
    """Income snapshots per period from submitted slips in scope and the current slip."""
    slips = frappe.get_all("Salary Slip", fields=["name", "start_date", "end_date", "total_working_hours", "qst_hours", "qst_skip"],
                           filters=[["employee", "=", doc.employee], ["docstatus", "=", 1], ["name", "!=", doc.name],
                                    ["start_date", ">=", scope_start], ["start_date", "<=", month_end(period)]])
    rows = frappe.get_all("Salary Detail", filters={"parenttype": "Salary Slip", "parent": ("in", [s.name for s in slips] or [""])},
                          fields=["parent", "parentfield", "salary_component", "amount", "statistical_component", "do_not_include_in_total"])
    types = component_types()
    months, skipped = {}, set()
    for slip in slips + [doc]:
        slip_rows = doc.earnings + doc.deductions if slip is doc else [r for r in rows if r.parent == slip.name]
        month = build_month(slip_rows, types, getdate(slip.start_date), getdate(slip.end_date),
                            flt(slip.qst_hours) or flt(slip.total_working_hours), employee)
        if slip is not doc and slip.qst_skip:
            skipped.add(month["period"])
        months[month["period"]] = merge(months.get(month["period"]), month)
    return months, skipped


def component_types():
    if "types" not in cache():
        cache()["types"] = dict(frappe.get_all("Salary Component", filters={"qst_type": ("is", "set")}, fields=["name", "qst_type"], as_list=True))
    return cache()["types"]


def build_month(rows, types, start, end, hours, employee):
    joining = getdate(employee.date_of_joining)
    relieving = getdate(employee.relieving_date) if employee.relieving_date else None
    month = {"period": start.replace(day=1), "periodic": 0, "aperiodic": 0, "thirteenth": 0, "hours": hours,
             "days": days_30(start, end, joining, relieving), "joining": joining, "relieving": relieving}
    for row in rows:
        key = TYPE_KEYS.get(types.get(row.salary_component))
        if key and not row.statistical_component and not row.do_not_include_in_total:
            month[key] += flt(row.amount) * (1 if row.parentfield == "earnings" else -1)
    return month


def merge(existing, month):
    if not existing:
        return month
    return dict(existing, days=min(30, existing["days"] + month["days"]), **{key: existing[key] + month[key] for key in SUM_KEYS})


def get_paid(doc, scope_start):
    """Quellensteuer already deducted per period on submitted slips."""
    return {getdate(row.period): flt(row.tax) for row in frappe.db.sql("""
        SELECT `detail`.`period`, SUM(`detail`.`tax`) AS `tax`
        FROM `tabQST Slip Detail` AS `detail`
        JOIN `tabSalary Slip` AS `slip` ON `slip`.`name` = `detail`.`parent`
        WHERE `detail`.`parenttype` = 'Salary Slip' AND `slip`.`docstatus` = 1
          AND `slip`.`employee` = %s AND `slip`.`name` != %s AND `detail`.`period` >= %s
        GROUP BY `detail`.`period`""", (doc.employee, doc.name, scope_start), as_dict=True)}


def get_record(employee, period):
    records = [r for r in employee.get("qst_records") or [] if getdate(r.valid_from) <= period]
    return max(records, key=lambda r: getdate(r.valid_from)) if records else None


def own_degree(employee, period):
    degrees = [d for d in employee.get("employment_degrees") or [] if getdate(d.date) <= month_end(period)]
    return flt(max(degrees, key=lambda d: getdate(d.date)).degree) if degrees else 100


def record_values(record, settings):
    return dict(record if isinstance(record, dict) else record.as_dict(), thirteenth_frequency=record.thirteenth_frequency or settings.thirteenth_frequency)


def calculate(employee, months, current_period, settings):
    """Expected tax per period with current employee data and latest tariffs."""
    results = {}
    for period in sorted(months):
        record = get_record(employee, period)
        month = months[period]
        result = results[period] = {"record": record if record and record.liable else None, "tax": 0, "rdi": 0, "rate": 0,
                                    "tariff": None, "model": None, "code": None, "error": None,
                                    "own_degree": own_degree(employee, period)}
        if not result["record"]:
            continue
        taxable = month["periodic"] + month["aperiodic"] + month["thirteenth"]
        result["code"] = tariff_code(record.tariff_group, record.children, record.church_tax)
        if record.other_employment == "Fixed Rate":
            result.update(rate=flt(record.fixed_rate), tax=tax_amount(taxable, flt(record.fixed_rate), 0, flt(settings.rounding)))
            continue
        if record.other_employment == "Fixed Amount":
            result["tax"] = flt(record.fixed_amount) if taxable else 0
            continue
        result["tariff"] = get_tariff(record.canton, period)
        if not result["tariff"]:
            result["error"] = _("No Quellensteuer tariff for canton {0} in {1}").format(record.canton, period.year)
            continue
        result["model"] = result["tariff"].calculation_model
        if result["model"] == "Annual":
            year_periods = [p for p in sorted(months) if p.year == period.year and p <= max(current_period, period)
                            and getattr(get_record(employee, p), "canton", None) == record.canton]
            last_record = get_record(employee, year_periods[-1])
            full_year = month["joining"] <= date(period.year, 1, 1) and (not month["relieving"] or month["relieving"] >= date(period.year, 12, 31))
            result["rdi"] = annual_rdi([months[p] for p in year_periods], record_values(last_record, settings),
                                       own_degree(employee, year_periods[-1]), full_year)
            income = result["rdi"] / 12
        else:
            result["rdi"] = income = monthly_rdi(month, record_values(record, settings), result["own_degree"])
        bracket = get_bracket(result["tariff"].name, result["code"], income)
        if not bracket:
            result["error"] = _("Tariff code {0} not found in {1}").format(result["code"], result["tariff"].name)
            continue
        result.update(rate=flt(bracket.rate), tax=tax_amount(taxable, flt(bracket.rate), flt(bracket.min_tax), flt(settings.rounding)))
    return results


def correction_allowed(result, doc, employee, settings):
    if result["model"] != "Annual" or settings.annual_model_correction != "Year-end":
        return True
    return getdate(doc.end_date).month == 12 or bool(employee.relieving_date and getdate(employee.relieving_date) <= getdate(doc.end_date))


def detail_row(result, month, period, paid, delta, entry_type):
    record = result["record"]
    return {
        "period": period,
        "entry_type": entry_type,
        "canton": record.canton if record else None,
        "model": result["model"],
        "tariff_code": result["code"],
        "qst_tariff": result["tariff"].name if result["tariff"] else None,
        "reason": (record.other_employment if record.other_employment != "None" else None) if record else _("Not liable"),
        "periodic": month["periodic"],
        "aperiodic": month["aperiodic"],
        "thirteenth": month["thirteenth"],
        "days": month["days"],
        "hours": month["hours"],
        "own_degree": result["own_degree"],
        "taxable_income": month["periodic"] + month["aperiodic"] + month["thirteenth"],
        "rate_determining_income": flt(result["rdi"], 2),
        "rate": result["rate"],
        "expected_tax": result["tax"],
        "previously_deducted": paid,
        "tax": delta,
    }


def set_deduction(doc, component, amount):
    row = next((r for r in doc.deductions if r.salary_component == component), None)
    if not amount:
        if row:
            doc.remove(row)
        return
    if not row:
        row = doc.append("deductions", {"salary_component": component})
    row.update({
        "abbr": frappe.get_cached_value("Salary Component", component, "salary_component_abbr"),
        "amount": amount,
        "default_amount": amount,
        "additional_amount": 0,
        "depends_on_payment_days": 0,
    })
