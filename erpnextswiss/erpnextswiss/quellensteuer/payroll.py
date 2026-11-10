from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, flt, fmt_money, formatdate, get_first_day, get_last_day, getdate

from erpnextswiss.erpnextswiss.quellensteuer.calculation import (
    CROSS_BORDER_GROUPS, MEDIAN_MODE, annual_rdi, days_30, monthly_rdi, tariff_code, tax_amount)
from erpnextswiss.erpnextswiss.quellensteuer.tariff import cache, get_bracket, get_tariff, prefetch

TYPE_KEYS = {"Periodic": "periodic", "Aperiodic": "aperiodic", "13th Salary": "thirteenth", "Replacement Income": "replacement"}
SUM_KEYS = ("periodic", "aperiodic", "thirteenth", "replacement", "hours")
DEGREE_MODES = ("Total Degree", "Extrapolate 100%")


def salary_slip_validate(doc, method=None):
    """Calculate Quellensteuer and corrections of earlier months on a salary slip."""
    settings = frappe.get_cached_doc("QST Settings")
    if not settings.enabled or doc.get("qst_skip"):
        return
    doc.flags.qst_error = None
    period = get_first_day(doc.start_date)
    precision = doc.precision("amount", "deductions") or 2
    scope_start = date(period.year - (1 if period.month <= cint(settings.prior_year_cutoff_month) else 0), 1, 1)
    employee = frappe.get_doc("Employee", doc.employee)
    months, skipped = collect_months(doc, employee, scope_start, period)
    paid = get_paid(doc, scope_start)
    locked = skipped | {p for p in months if p < getdate(settings.go_live_date)}
    later_slip = frappe.db.exists("Salary Slip", {"employee": doc.employee, "docstatus": 1, "start_date": (">", get_last_day(period))})
    details, current, correction, pending = [], 0, 0, 0
    for month_period, result in sorted(calculate(employee, months, period, settings, precision).items()):
        delta = flt(result["tax"] - paid.get(month_period, 0), precision)
        if result["error"] and (month_period == period or not (later_slip or month_period in locked)):
            doc.flags.qst_error = doc.flags.qst_error or result["error"]
            frappe.msgprint(result["error"], title=_("Quellensteuer"), indicator="red")
            if month_period != period:
                continue
        if month_period == period:
            current = delta
            if result.get("fallback"):
                frappe.msgprint(_("No cross-border certificate covering {0:%m.%Y} for tariff group {1}. The ordinary tariff {2} has been applied.").format(
                    period, result["record"].tariff_group, result["code"]), title=_("Quellensteuer"), indicator="orange")
        elif (month_period in locked or not delta or abs(delta) < flt(settings.min_correction)
              or not correction_allowed(result, doc, employee, settings)):
            continue
        elif later_slip:
            pending += delta
            continue
        else:
            correction += delta
        if month_period == period and not (result["record"] or delta):
            continue
        details.append(detail_row(result, months[month_period], month_period, paid.get(month_period, 0), delta,
                                  "Current" if month_period == period else "Correction", precision))
    if pending:
        frappe.msgprint(_("Quellensteuer corrections of {0} for earlier months were not applied because a salary slip for a later month is already submitted. "
                          "Corrections are made on the newest salary slip.").format(fmt_money(flt(pending, 2), currency=doc.get("currency"))),
                        title=_("Quellensteuer"), indicator="orange")
    doc.set("qst_details", details)
    set_deduction(doc, settings.qst_component, current)
    set_deduction(doc, settings.correction_component, flt(correction, precision))
    doc.set_net_pay()
    doc.compute_year_to_date()
    doc.compute_month_to_date()
    doc.compute_component_wise_year_to_date()


def salary_slip_before_submit(doc, method=None):
    if doc.flags.qst_error:
        frappe.throw(doc.flags.qst_error, title=_("Quellensteuer"))


def payroll_entry_validate(doc, method=None):
    """Warn about employees whose Quellensteuer cannot be determined for this period."""
    issues = check_employees(doc)
    if issues:
        frappe.msgprint("<br>".join("{0}: {1}".format(issue["employee_name"], issue["issue"]) for issue in issues),
                        title=_("Quellensteuer"), indicator="orange")


@frappe.whitelist()
def preflight(payroll_entry):
    """Employees of a payroll entry whose Quellensteuer cannot be determined; loads the tariff codes needed."""
    doc = frappe.get_doc("Payroll Entry", payroll_entry)
    doc.check_permission("read")
    return check_employees(doc)


def check_employees(doc):
    """Check the Quellensteuer data of all employees of a payroll entry before salary slips are created."""
    settings = frappe.get_cached_doc("QST Settings")
    if not settings.enabled or not doc.get("employees"):
        return []
    period = get_first_day(doc.start_date)
    employees = [row.employee for row in doc.employees]
    liable = set(frappe.get_all("QST Employee Record", filters={"parenttype": "Employee", "parent": ("in", employees), "liable": 1},
                                pluck="parent", distinct=True))
    issues = []
    for name in employees:
        problem = employee_issue(frappe.get_doc("Employee", name), period) if name in liable else None
        if problem:
            issues.append(problem)
    return issues


def employee_issue(employee, period):
    """What keeps the Quellensteuer of an employee from being calculated in a period, if anything."""
    record = get_record(employee, period)
    if not record or not record.liable or record.tax_override:
        return None

    def issue(message):
        return {"employee": employee.name, "employee_name": employee.employee_name, "issue": message}

    if record.other_employment in DEGREE_MODES and not own_degree(employee, period):
        return issue(_("No employment degree for {0:%m.%Y}, required for {1}").format(period, _(record.other_employment)))
    tariff = get_tariff(record.canton, period)
    if not tariff:
        return issue(_("No Quellensteuer tariff for canton {0} in {1}").format(record.canton, period.year))
    if record.other_employment == MEDIAN_MODE and not tariff.get("median_value"):
        return issue(_("No median value in tariff {0}, required for {1}").format(tariff.name, _(MEDIAN_MODE)))
    code = tariff_code(effective_group(record, period), record.children, record.church_tax)
    if not prefetch(tariff.name, code):
        return issue(_("Tariff code {0} not found in {1}").format(code, tariff.name))
    return None


def collect_months(doc, employee, scope_start, period):
    """Income snapshots per period from submitted slips in scope and the current slip."""
    slips = frappe.get_all("Salary Slip", fields=["name", "start_date", "end_date", "total_working_hours", "qst_hours", "qst_skip"],
                           filters=[["employee", "=", doc.employee], ["docstatus", "=", 1], ["name", "!=", doc.name],
                                    ["start_date", ">=", scope_start], ["start_date", "<=", get_last_day(period)]])
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
    month = {"period": get_first_day(start), "periodic": 0, "aperiodic": 0, "thirteenth": 0, "replacement": 0, "hours": hours,
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


def effective_group(record, period):
    """Tariff group, replaced by the ordinary group without a cross-border certificate covering the month."""
    ordinary = CROSS_BORDER_GROUPS.get(record.tariff_group)
    if ordinary and not (record.get("cross_border_valid_until") and getdate(record.cross_border_valid_until) >= get_last_day(period)):
        return ordinary
    return record.tariff_group


def same_canton_all_year(employee, year, canton):
    """True if the employee is liable in the same canton for the whole year (KS45 section 8)."""
    records = [get_record(employee, date(year, 1, 1))] + [
        r for r in employee.get("qst_records") or [] if date(year, 1, 1) < getdate(r.valid_from) <= date(year, 12, 1)]
    return all(r and r.liable and r.canton == canton for r in records)


def own_degree(employee, period):
    degrees = [d for d in employee.get("employment_degrees") or [] if getdate(d.date) <= get_last_day(period)]
    return flt(max(degrees, key=lambda d: getdate(d.date)).degree) if degrees else None


def receives_thirteenth(employee, period):
    """True if the employee's salary structure in a month contains a 13th salary component."""
    key = ("thirteenth", employee, period)
    if key not in cache():
        structure = frappe.db.get_value("Salary Structure Assignment", {"employee": employee, "docstatus": 1, "from_date": ("<=", get_last_day(period))},
                                        "salary_structure", order_by="from_date desc")
        components = [name for name, qst_type in component_types().items() if qst_type == "13th Salary"]
        cache()[key] = bool(structure and components and frappe.db.exists("Salary Detail", {
            "parenttype": "Salary Structure", "parent": structure, "parentfield": "earnings", "salary_component": ("in", components)}))
    return cache()[key]


def record_values(record, settings, tariff):
    return dict(record if isinstance(record, dict) else record.as_dict(), thirteenth_frequency=settings.thirteenth_frequency,
                median_value=flt(tariff.get("median_value")))


def calculate(employee, months, current_period, settings, precision=2):
    """Expected tax per period with current employee data and latest tariffs."""
    results = {}
    for period in sorted(months):
        record = get_record(employee, period)
        month = months[period]
        result = results[period] = {"record": record if record and record.liable else None, "tax": 0, "rdi": 0, "rate": 0,
                                    "tariff": None, "model": None, "code": None, "error": None,
                                    "min_tax": 0, "income_from": 0, "own_degree": own_degree(employee, period)}
        if not result["record"]:
            continue
        taxable = month["periodic"] + month["aperiodic"] + month["thirteenth"] + month.get("replacement", 0)
        group = effective_group(record, period)
        result.update(code=tariff_code(group, record.children, record.church_tax), fallback=group != record.tariff_group)
        if record.tax_override == "Fixed Rate":
            result.update(rate=flt(record.fixed_rate), tax=flt(tax_amount(taxable, flt(record.fixed_rate)), precision))
            continue
        if record.tax_override == "Fixed Amount":
            result["tax"] = flt(record.fixed_amount) if taxable else 0
            continue
        if record.other_employment in DEGREE_MODES and not result["own_degree"]:
            result["error"] = _("No employment degree for {0} in {1:%m.%Y}, required for {2}").format(employee.name, period, _(record.other_employment))
            continue
        result["tariff"] = get_tariff(record.canton, period)
        if not result["tariff"]:
            result["error"] = _("No Quellensteuer tariff for canton {0} in {1}").format(record.canton, period.year)
            continue
        result["model"] = result["tariff"].calculation_model
        if record.other_employment == MEDIAN_MODE and not result["tariff"].get("median_value"):
            result["error"] = _("No median value in tariff {0}, required for {1}").format(result["tariff"].name, _(MEDIAN_MODE))
            continue
        if result["model"] == "Annual":
            year_periods = [p for p in sorted(months) if p.year == period.year and p <= max(current_period, period)
                            and getattr(get_record(employee, p), "canton", None) == record.canton]
            last_record = get_record(employee, year_periods[-1])
            full_year = (year_periods[0].month == 1 and month["joining"] <= date(period.year, 1, 1)
                         and (not month["relieving"] or month["relieving"] >= date(period.year, 12, 31))
                         and same_canton_all_year(employee, period.year, record.canton))
            project = bool(settings.project_thirteenth) and receives_thirteenth(employee.name, year_periods[-1])
            result["rdi"] = annual_rdi([months[p] for p in year_periods], record_values(last_record, settings, result["tariff"]),
                                       own_degree(employee, year_periods[-1]) or 100, full_year, project)
            income = result["rdi"] / 12
        else:
            result["rdi"] = income = monthly_rdi(month, record_values(record, settings, result["tariff"]), result["own_degree"] or 100)
        bracket = get_bracket(result["tariff"].name, result["code"], income)
        if not bracket:
            result["error"] = _("Tariff code {0} not found in {1}").format(result["code"], result["tariff"].name)
            continue
        result.update(rate=flt(bracket.rate), min_tax=flt(bracket.min_tax), income_from=flt(bracket.income_from),
                      tax=flt(tax_amount(taxable, flt(bracket.rate), flt(bracket.min_tax)), precision))
    return results


def correction_allowed(result, doc, employee, settings):
    if result["model"] != "Annual" or settings.annual_model_correction != "Year-end":
        return True
    return getdate(doc.end_date).month == 12 or bool(employee.relieving_date and getdate(employee.relieving_date) <= getdate(doc.end_date))


def reason(result, record):
    """Why the tax of a period was calculated the way it was; stored untranslated, displayed translated."""
    if not record:
        return "Not liable"
    if result.get("fallback"):
        return "No cross-border certificate"
    if record.tax_override:
        return record.tax_override
    return record.other_employment if record.other_employment != "None" else None


def explanation(row, precision=2):
    """One-line formula of how the tax of a detail row was determined, in the language of the reader."""
    def money(value):
        return fmt_money(flt(value, precision))

    if row.get("reason") == "Not liable":
        return _("Not liable")
    if row.get("reason") == "Fixed Amount":
        return _("Fixed amount of the tax office: {0}").format(money(row.get("expected_tax")))
    parts = [_("Taxable {0}").format(money(row.get("taxable_income")))]
    if row.get("reason") == "Fixed Rate":
        parts.append(_("fixed rate {0}%").format(flt(row.get("rate"))))
    else:
        parts.insert(0, _("Annual model") if row.get("model") == "Annual" else _("Monthly model"))
        if row.get("hourly_wage") and row.get("hours"):
            parts.append(_("{0} hours").format(flt(row.get("hours"), 2)))
        elif cint(row.get("days")) != 30:
            parts.append(_("{0} of 30 days").format(cint(row.get("days"))))
        if row.get("reason"):
            parts.append(_(row.get("reason"), context="QST Slip Detail"))
        if row.get("own_degree") and row.get("reason") in DEGREE_MODES:
            parts.append(_("employment degree {0}%").format(flt(row.get("own_degree"))))
        parts.append(_("rate-determining income {0}").format(money(row.get("rate_determining_income"))))
        bracket = [row.get("tariff_code"), _("{0}%").format(flt(row.get("rate")))]
        if flt(row.get("income_from")):
            bracket.append(_("from {0}").format(money(row.get("income_from"))))
        parts.append(" ".join(str(part) for part in bracket))
        if flt(row.get("min_tax")) and flt(row.get("taxable_income")) * flt(row.get("rate")) / 100 < flt(row.get("min_tax")):
            parts.append(_("minimum tax {0}").format(money(row.get("min_tax"))))
    parts.append(_("tax {0}").format(money(row.get("expected_tax"))))
    return " \u00b7 ".join(str(part) for part in parts)


@frappe.whitelist()
def explain_slip(salary_slip):
    """Quellensteuer formulas of a salary slip, rendered from its stored detail rows."""
    doc = frappe.get_doc("Salary Slip", salary_slip)
    doc.check_permission("read")
    precision = doc.precision("amount", "deductions") or 2
    return [{"period": formatdate(row.period), "entry_type": _(row.entry_type, context="QST Slip Detail"),
             "calculation": explanation(row, precision)} for row in doc.get("qst_details") or []]


def detail_row(result, month, period, paid, delta, entry_type, precision=2):
    record = result["record"]
    taxable = month["periodic"] + month["aperiodic"] + month["thirteenth"] + month.get("replacement", 0)
    return {
        "period": period,
        "entry_type": entry_type,
        "canton": record.canton if record else None,
        "model": result["model"],
        "tariff_code": result["code"],
        "qst_tariff": result["tariff"].name if result["tariff"] else None,
        "reason": reason(result, record),
        "periodic": month["periodic"],
        "aperiodic": month["aperiodic"],
        "thirteenth": month["thirteenth"],
        "replacement": month.get("replacement", 0),
        "days": month["days"],
        "hours": month["hours"],
        "hourly_wage": 1 if record and record.hourly_wage else 0,
        "own_degree": result["own_degree"],
        "taxable_income": taxable,
        "rate_determining_income": flt(result["rdi"], precision),
        "rate": result["rate"],
        "income_from": result["income_from"],
        "min_tax": result["min_tax"],
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
