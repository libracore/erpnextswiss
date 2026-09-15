import calendar
from datetime import date

PERIOD_MONTHS = {"Quarterly": 3, "Half-yearly": 6, "Yearly": 12}


def round_to(value, step=0.05):
    """Round an amount to the given step (e.g. 0.05 CHF)."""
    return round(round(value / step) * step, 2) if step else round(value, 2)


def month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def add_months(day, months):
    year, month = divmod(day.month - 1 + months, 12)
    return date(day.year + year, month + 1, 1)


def day_30(day):
    """Day of month on a 30-day basis (KS45 6.6)."""
    return 30 if day.day == 31 or (day.month == 2 and day.day >= 28) else day.day


def days_30(start, end, joining=None, relieving=None):
    """Employment days within one month on a 30-day basis."""
    first = max(start, joining) if joining else start
    last = min(end, relieving) if relieving else end
    return 0 if last < first else min(30, day_30(last) - day_30(first) + 1)


CROSS_BORDER_GROUPS = {"L": "A", "M": "B", "N": "C", "P": "H", "Q": "G", "R": "A", "S": "B", "T": "C", "U": "H", "V": "G", "SF": "A"}


def tariff_code(group, children=0, church_tax=False):
    """Build the ESTV tariff code, e.g. B2Y."""
    if group == "SF":
        return "SFN"
    if group in ("G", "Q", "V"):
        return f"{group}9N"
    return f"{group}{min(int(children or 0), 9)}{'Y' if church_tax else 'N'}"


def thirteenth_rdi(amount, frequency, end, joining=None, relieving=None):
    """Rate-determining part of a 13th salary paid in the month of end (KS45 6.3/6.6)."""
    if not amount or frequency not in PERIOD_MONTHS:
        return amount or 0
    start = date(end.year, end.month - (end.month - 1) % PERIOD_MONTHS[frequency], 1)
    worked = sum(days_30(add_months(start, i), month_end(add_months(start, i)), joining, relieving)
                 for i in range(PERIOD_MONTHS[frequency]))
    return amount / worked * PERIOD_MONTHS[frequency] * 30 if worked else amount


def scale_to_degree(amount, record, own_degree):
    """Convert periodic income for other employments (KS45 6.4, rules 1 and 2)."""
    mode = record.get("other_employment")
    if mode == "Total Degree" and own_degree and record.get("total_degree"):
        return amount * record["total_degree"] / own_degree
    if mode == "Extrapolate 100%" and own_degree:
        return amount * 100 / own_degree
    return amount


def monthly_rdi(month, record, own_degree=100):
    """Rate-determining monthly income under the monthly model (KS45 section 6)."""
    hourly = record.get("hourly_wage") and month.get("hours")
    periodic = month["periodic"] + (0 if hourly else month.get("replacement", 0))
    thirteenth = thirteenth_rdi(month["thirteenth"], record.get("thirteenth_frequency") or "Yearly", month_end(month["period"]),
                                month.get("joining"), month.get("relieving"))
    if hourly:
        base = periodic / month["hours"] * 180 + thirteenth
    else:
        days = month.get("days", 30)
        base = scale_to_degree((periodic * 30 / days if 0 < days < 30 else periodic) + thirteenth, record, own_degree)
        if record.get("other_employment") == "Other Income":
            base += record.get("other_income") or 0
    return base + month["aperiodic"]


def thirteenth_covered_months(months, frequency):
    """Months of the year covered by 13th salary payouts so far."""
    size = PERIOD_MONTHS.get(frequency, 12)
    paid = [month["period"].month for month in months if month["thirteenth"]]
    return min(12, -(-max(paid) // size) * size) if paid else 0


def annual_rdi(months, record, own_degree=100, full_year=False, project_thirteenth=False):
    """Rate-determining annual income under the annual model from the months so far (KS45 section 7)."""
    hours = sum(month.get("hours") or 0 for month in months)
    hourly = record.get("hourly_wage") and hours
    periodic = [month["periodic"] + (0 if hourly else month.get("replacement", 0)) for month in months]
    aperiodic = sum(month["aperiodic"] for month in months)
    thirteenth = sum(month["thirteenth"] for month in months)
    if hourly:
        return sum(periodic) / hours * 2160 + thirteenth + aperiodic
    if full_year:
        base = sum(periodic[:-1]) + periodic[-1] * (13 - months[-1]["period"].month)
    else:
        days = sum(month.get("days", 30) for month in months)
        base = sum(periodic) * 360 / days if days else 0
    if project_thirteenth:
        base += base / 12 * (12 - thirteenth_covered_months(months, record.get("thirteenth_frequency") or "Yearly")) / 12
    base = scale_to_degree(base + thirteenth, record, own_degree)
    if record.get("other_employment") == "Other Income":
        base += (record.get("other_income") or 0) * 12
    return base + aperiodic


def tax_amount(taxable, rate, min_tax=0, rounding=0.05):
    """Tax for a taxable amount: rate in percent, at least the minimum tax."""
    amount = taxable * rate / 100
    if taxable > 0 and amount < min_tax:
        amount = min_tax
    return round_to(amount, rounding)
