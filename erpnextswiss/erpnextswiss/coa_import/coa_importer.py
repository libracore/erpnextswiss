# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
import pandas as pd
from frappe.utils import get_bench_path

'''
    execute with: sudo bench execute erpnextswiss.erpnextswiss.coa_import.coa_importer.import_coa --kwargs "{'company': '<company name>'}"
    
    Workflow:
    1. Validate company
    2. Remove old company account defaults (company Settings)
    3. Delete old chart of accounts from company
    4. Create new chart of accounts incl. company account defaults (based on csv template)
'''

def import_coa(company=False, file_path=False):
    # Validate company
    if not company:
        frappe.throw('Missing company')
    
    try:
        company = frappe.get_doc("Company", company)
    except:
        frappe.throw('Company ({company}) not found'.format(company=company))
    
    print("Company found")
    
    # Remove old company account defaults (company Settings)
    print("removing old company account defaults...")
    remove_old_company_account_defaults(company.name)
    
    # Delete old chart of accounts from company
    print("deleting old chart of accounts from company...")
    delete_old_accounts(company.name)
    
    # Create new chart of accounts incl. company account defaults (based on csv template)
    # read accounts template csv
    if not file_path:
        file_path = "{0}/apps/erpnextswiss/erpnextswiss/erpnextswiss/coa_import/accounts_template.csv".format(get_bench_path())
    df = pd.read_csv(file_path)
    qty = len(df.index)
    print("found {qty} entries in template csv".format(qty=qty))
    
    # loop trough accounts template and create new accounts
    loop = 1
    for index, row in df.iterrows():
        print("create account No. {loop} of {qty}".format(loop=loop, qty=qty))
        create_account(company.name, company.abbr, row)
        loop += 1
    print("finish")

def create_account(company, abbr, row):
    # create new account
    new_account = frappe.get_doc({
        "doctype": "Account",
        "account_name": get_value(row, 'account_name'),
        "company": company,
        "parent_account": (" - ").join((get_value(row, 'parent_account'), abbr)) if get_value(row, 'parent_account') else '',
        "account_number": get_value(row, 'account_number'),
        "is_group": get_value(row, 'is_group'),
        "root_type": get_value(row, 'root_type'),
        "report_type": get_value(row, 'report_type'),
        "account_currency": get_value(row, 'account_currency'),
        "account_type": get_value(row, 'account_type'),
        "tax_rate": get_value(row, 'tax_rate'),
        "freeze_account": get_value(row, 'freeze_account'),
        "balance_must_be": get_value(row, 'balance_must_be'),
        "iban": get_value(row, 'iban'),
        "bic": get_value(row, 'bic')
    })
    new_account.flags.ignore_root_company_validation = True
    new_account.flags.ignore_mandatory = True
    new_account.insert()
    frappe.db.commit()
    
    # set new account as company default account if necessary
    if get_value(row, 'company_default_account'):
        set_as_company_default(company, new_account.name, get_value(row, 'company_default_account'))

# get dataframe value of accounts template row
def get_value(row, value):
    value = row[value]
    if not pd.isnull(value):
        try:
            if isinstance(value, str):
                return value.strip()
            else:
                return value
        except:
            return value
    else:
        return ''

def set_as_company_default(company, new_account, company_default):
    frappe.db.set_value('Company', company, company_default, new_account)
    frappe.db.commit()

def remove_old_company_account_defaults(company):
    company = frappe.get_doc("Company", company)
    
    company.default_receivable_account = ''
    company.default_payable_account = ''
    company.default_employee_advance_account = ''
    company.default_income_account = ''
    company.write_off_account = ''
    company.default_payroll_payable_account = ''
    company.exchange_gain_loss_account = ''
    company.disposal_account = ''
    
    frappe.local.flags.ignore_chart_of_accounts = True
    
    company.save()
    frappe.db.commit()

def delete_old_accounts(company):
    accounts_to_delete = frappe.db.sql("""SELECT `name` FROM `tabAccount` WHERE `company` = '{company}'""".format(company=company), as_dict=True)
    for account_to_delete in accounts_to_delete:
        delete = frappe.db.sql("""DELETE FROM `tabAccount` WHERE `name` = '{account_to_delete}'""".format(account_to_delete=account_to_delete.name), as_list=True)
    frappe.db.commit()
