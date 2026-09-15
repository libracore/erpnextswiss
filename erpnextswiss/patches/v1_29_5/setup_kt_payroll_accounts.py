# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe


COMPANY = "KT Wärmesysteme AG"
CURRENCY = "CHF"

EXPENSE_PARENT = "50 - Personalaufwand - KT-Wärme"
LIABILITY_PARENT = "220 - Übrige kurzfristige Verbindlichkeiten - KT-Wärme"
PAYROLL_PAYABLE_ACCOUNT = "2035 - Lohndurchlaufskonto - KT-Wärme"
PAYROLL_PAYABLE_ACCOUNT_NUMBER = "2035"


EXPENSE_ACCOUNTS = [
    {
        "account_number": "5710",
        "account_name": "AHV/IV/EO/ALV/FAK",
        "account_type": "Expense Account",
    },
    {
        "account_number": "5720",
        "account_name": "Berufliche Vorsorge (BVG)",
        "account_type": "Expense Account",
    },
    {
        "account_number": "5730",
        "account_name": "Unfallversicherung SUVA",
        "account_type": "Expense Account",
    },
    {
        "account_number": "5740",
        "account_name": "Krankentaggeldversicherung",
        "account_type": "Expense Account",
    },
    {
        "account_number": "5750",
        "account_name": "UVG-Zusatzversicherung",
        "account_type": "Expense Account",
    },
]

LIABILITY_ACCOUNTS = [
    {
        "account_number": "2271",
        "account_name": "Verbindlichkeiten AHV/IV/EO/ALV/FAK",
    },
    {
        "account_number": "2272",
        "account_name": "Verbindlichkeiten BVG",
    },
    {
        "account_number": "2273",
        "account_name": "Verbindlichkeiten Unfallversicherung SUVA",
    },
    {
        "account_number": "2274",
        "account_name": "Verbindlichkeiten KTG",
    },
    {
        "account_number": "2275",
        "account_name": "Verbindlichkeiten UVG-Zusatz",
    },
]

SALARY_COMPONENTS = [
    {
        "name": "13. Monatslohn",
        "abbr": "M13",
        "component_type": "Earning",
        "account_number": "5000",
    },
    {
        "name": "Kinderzulage",
        "abbr": "KIZ",
        "component_type": "Earning",
        "account_number": "2271",
        "description": (
            "Familienzulagen werden als Durchlauf über die Familienausgleichskasse "
            "und nicht als Lohnaufwand gebucht."
        ),
    },
    {
        "name": "AHV/IV/EO Arbeitnehmer",
        "abbr": "AHV",
        "component_type": "Deduction",
        "account_number": "2271",
    },
    {
        "name": "ALV Arbeitnehmer",
        "abbr": "ALV",
        "component_type": "Deduction",
        "account_number": "2271",
    },
    {
        "name": "BVG Arbeitnehmer",
        "abbr": "PK",
        "component_type": "Deduction",
        "account_number": "2272",
    },
    {
        "name": "UVG NBU Arbeitnehmer",
        "abbr": "NBUV",
        "component_type": "Deduction",
        "account_number": "2273",
    },
    {
        "name": "KTG Arbeitnehmer",
        "abbr": "KTG",
        "component_type": "Deduction",
        "account_number": "2274",
    },
    {
        "name": "UVG-Zusatz Arbeitnehmer",
        "abbr": "UVGZ",
        "component_type": "Deduction",
        "account_number": "2275",
    },
    {
        "name": "AHV/IV/EO/ALV/FAK Arbeitgeber Aufwand",
        "abbr": "AHVAGW",
        "component_type": "Earning",
        "account_number": "5710",
        "do_not_include_in_total": 1,
    },
    {
        "name": "AHV/IV/EO/ALV/FAK Arbeitgeber Verbindlichkeit",
        "abbr": "AHVAGV",
        "component_type": "Deduction",
        "account_number": "2271",
        "do_not_include_in_total": 1,
    },
    {
        "name": "BVG Arbeitgeber Aufwand",
        "abbr": "BVGAGW",
        "component_type": "Earning",
        "account_number": "5720",
        "do_not_include_in_total": 1,
    },
    {
        "name": "BVG Arbeitgeber Verbindlichkeit",
        "abbr": "BVGAGV",
        "component_type": "Deduction",
        "account_number": "2272",
        "do_not_include_in_total": 1,
    },
    {
        "name": "UVG/SUVA Arbeitgeber Aufwand",
        "abbr": "UVGAGW",
        "component_type": "Earning",
        "account_number": "5730",
        "do_not_include_in_total": 1,
    },
    {
        "name": "UVG/SUVA Arbeitgeber Verbindlichkeit",
        "abbr": "UVGAGV",
        "component_type": "Deduction",
        "account_number": "2273",
        "do_not_include_in_total": 1,
    },
    {
        "name": "KTG Arbeitgeber Aufwand",
        "abbr": "KTGAGW",
        "component_type": "Earning",
        "account_number": "5740",
        "do_not_include_in_total": 1,
    },
    {
        "name": "KTG Arbeitgeber Verbindlichkeit",
        "abbr": "KTGAGV",
        "component_type": "Deduction",
        "account_number": "2274",
        "do_not_include_in_total": 1,
    },
    {
        "name": "UVG-Zusatz Arbeitgeber Aufwand",
        "abbr": "UVGZAGW",
        "component_type": "Earning",
        "account_number": "5750",
        "do_not_include_in_total": 1,
    },
    {
        "name": "UVG-Zusatz Arbeitgeber Verbindlichkeit",
        "abbr": "UVGZAGV",
        "component_type": "Deduction",
        "account_number": "2275",
        "do_not_include_in_total": 1,
    },
]

EXISTING_COMPONENT_ACCOUNTS = {
    "Basic": "5000",
    "Arrear": "5000",
    "Leave Encashment": "5000",
    "Pauschalspesen Geschäftsleitung": "5800",
}


def execute():
    if not frappe.db.exists("Company", COMPANY):
        return

    payroll_payable_account = get_account_name_by_number(PAYROLL_PAYABLE_ACCOUNT_NUMBER) or PAYROLL_PAYABLE_ACCOUNT
    ensure_account_type(payroll_payable_account, "Payable")
    set_company_payroll_payable_account(payroll_payable_account)

    for account in EXPENSE_ACCOUNTS:
        ensure_account(
            parent_account=EXPENSE_PARENT,
            root_type="Expense",
            report_type="Profit and Loss",
            **account
        )

    for account in LIABILITY_ACCOUNTS:
        ensure_account(
            parent_account=LIABILITY_PARENT,
            root_type="Liability",
            report_type="Balance Sheet",
            **account
        )

    for component_name, account_number in EXISTING_COMPONENT_ACCOUNTS.items():
        account = get_account_name_by_number(account_number)
        if frappe.db.exists("Salary Component", component_name) and account:
            ensure_component_account(component_name, account)

    for component in SALARY_COMPONENTS:
        ensure_salary_component(**component)

    frappe.db.commit()


def ensure_account(
    account_number,
    account_name,
    parent_account,
    root_type,
    report_type,
    account_type=None,
):
    if not frappe.db.exists("Account", parent_account):
        frappe.throw("Missing parent account {0}".format(parent_account))

    existing = frappe.db.get_value(
        "Account",
        {"company": COMPANY, "account_number": account_number},
        "name",
    )

    values = {
        "account_name": account_name,
        "parent_account": parent_account,
        "root_type": root_type,
        "report_type": report_type,
        "account_currency": CURRENCY,
        "is_group": 0,
    }
    if account_type is not None:
        values["account_type"] = account_type

    if existing:
        doc = frappe.get_doc("Account", existing)
        changed = False
        for field, value in values.items():
            if doc.get(field) != value:
                doc.set(field, value)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Account",
            "company": COMPANY,
            "account_number": account_number,
            **values,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def ensure_account_type(account, account_type):
    if frappe.db.exists("Account", account):
        current = frappe.db.get_value("Account", account, "account_type")
        if current != account_type:
            frappe.db.set_value("Account", account, "account_type", account_type)


def set_company_payroll_payable_account(account):
    if frappe.db.has_column("Company", "default_payroll_payable_account"):
        current = frappe.db.get_value("Company", COMPANY, "default_payroll_payable_account")
        if current != account:
            frappe.db.set_value("Company", COMPANY, "default_payroll_payable_account", account)


def ensure_salary_component(
    name,
    abbr,
    component_type,
    account_number,
    description=None,
    do_not_include_in_total=0,
):
    account = get_account_name_by_number(account_number)
    if not account:
        frappe.throw("Missing account number {0}".format(account_number))

    values = {
        "salary_component": name,
        "salary_component_abbr": abbr,
        "type": component_type,
        "do_not_include_in_total": do_not_include_in_total,
        "do_not_include_in_accounts": 0,
        "disabled": 0,
    }
    if description is not None:
        values["description"] = description

    if frappe.db.exists("Salary Component", name):
        doc = frappe.get_doc("Salary Component", name)
        for field, value in values.items():
            if doc.meta.has_field(field):
                doc.set(field, value)
    else:
        doc = frappe.get_doc({"doctype": "Salary Component", **values})

    upsert_component_account_row(doc, account)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)


def ensure_component_account(component_name, account):
    doc = frappe.get_doc("Salary Component", component_name)
    upsert_component_account_row(doc, account)
    doc.save(ignore_permissions=True)


def upsert_component_account_row(component, account):
    row = None
    for existing in component.get("accounts"):
        if existing.company == COMPANY:
            row = existing
            break

    if row:
        row.account = account
    else:
        component.append("accounts", {"company": COMPANY, "account": account})


def get_account_name_by_number(account_number):
    return frappe.db.get_value(
        "Account",
        {"company": COMPANY, "account_number": account_number},
        "name",
    )
