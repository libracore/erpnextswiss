# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_manager import save_file, remove_all

""" Jinja hook to create account sheets """
def get_account_sheets(fiscal_year, company=None):
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    _opening_debit = 0
    _opening_credit = 0
    account_data = []
    if company:
        accounts = frappe.get_all("Account", filters={'disabled': 0, 'company': company}, fields=['name', 'report_type'], order_by='name')
    else:
        accounts = frappe.get_all("Account", filters={'disabled': 0}, fields=['name', 'report_type'], order_by='name')
    for account in accounts:
        _balance = 0
        _data = {'account': account.name, 'transactions': [], 'report_type': account.report_type}
        transactions = frappe.get_all("GL Entry", filters=[
            ['account', '=', account.name],
            ['posting_date', '>=', fy.year_start_date],
            ['posting_date', '<=', fy.year_end_date]
        ], fields=['posting_date', 'debit', 'credit', 'remarks', 'voucher_no', 'creation', 'is_opening'],
        order_by='posting_date')
        if transactions:
            # calculate opening for balance sheet accounts
            # reset counters
            _opening_debit = 0
            _opening_credit = 0 
            if account.report_type == "Balance Sheet":
                # compute opening balance
                opening_transactions = frappe.get_all("GL Entry", filters=[
                  ['account', '=', account.name],
                  ['posting_date', '<', fy.year_start_date]
                ], fields=['debit', 'credit'])     
                # compute debit and credit at opening
                for opening_txn in opening_transactions:
                    _opening_debit += opening_txn.debit
                    _opening_credit += opening_txn.credit
                # consolidate debit/credit
                if _opening_debit > _opening_credit:
                    _delta = _opening_debit - _opening_credit
                    _opening_debit = _delta
                    _opening_credit = 0
                else:
                    _delta = _opening_credit - _opening_debit
                    _opening_debit = 0
                    _opening_credit = _delta
                _data['opening_debit'] = _opening_debit
                _data['opening_credit'] = _opening_credit
                _balance = (_opening_debit - _opening_credit)
            # reset counters for period sum
            _opening_debit = 0
            _opening_credit = 0 
            # loop through transactions
            for transaction in transactions:
                # update current debit/credit
                _opening_debit += transaction.debit
                _opening_credit += transaction.credit
                _balance += (transaction.debit - transaction.credit)
                _data['transactions'].append({
                    'posting_date': transaction.posting_date,
                    'debit': transaction.debit,
                    'credit': transaction.credit,
                    'balance': _balance,
                    'voucher_no': transaction.voucher_no,
                    'remarks': transaction.remarks
                })
            # compute closing balance, debit and credit ar sums of transactions
            _data['closing_debit'] = _opening_debit
            _data['closing_credit'] = _opening_credit
            _data['closing_balance'] = _balance
            # append data to storage
            account_data.append(_data)
    return account_data

# background job to create long pdf for fiscal year
@frappe.whitelist()
def enqueue_build_long_fiscal_year_print(fiscal_year):
    kwargs={
        'fiscal_year': fiscal_year
    }

    enqueue("erpnextswiss.erpnextswiss.finance.build_long_fiscal_year_print",
        queue='long',
        timeout=15000,
        **kwargs)
    return

def build_long_fiscal_year_print(fiscal_year):
    fiscal_year = frappe.get_doc("Fiscal Year", fiscal_year)
    # clear attached files
    remove_all("Fiscal Year", fiscal_year.name)
    for c in fiscal_year.companies:
        # create html
        if not c.print_format:
            frappe.log_error( _("Please specify a print format for company {0}", _("Print Fiscal Year") ) )
        html = frappe.get_print("Fiscal Year", fiscal_year.name, print_format=c.print_format)
        # create pdf
        pdf = frappe.utils.pdf.get_pdf(html)
        # save and attach pdf
        file_name = ("{0}_{1}.pdf".format(fiscal_year.name, c.company)).replace(" ", "_").replace("/", "_")
        save_file(file_name, pdf, "Fiscal Year", fiscal_year.name, is_private=1)
    return

"""
Function to build customer credit statement of account

Jinja-endpoint

Company selection: defined through accounts
"""
def get_customer_ledger(accounts, customer, in_account_currency=False):
    currency_selector = """`tabGL Entry`.`credit` - `tabGL Entry`.`debit`"""
    if in_account_currency:
        currency_selector = """`tabGL Entry`.`credit_in_account_currency` - `tabGL Entry`.`debit_in_account_currency`"""
        
    sql_query = """
        SELECT
            `tabGL Entry`.`posting_date` AS `posting_date`,
            {currency_selector} AS `amount`,
            `tabGL Entry`.`voucher_no` AS `voucher_no`
        FROM `tabGL Entry`
        LEFT JOIN `tabPayment Entry` ON `tabPayment Entry`.`name` = `tabGL Entry`.`voucher_no`
        WHERE 
            `tabGL Entry`.`account` IN ("{accounts}")
            AND (`tabGL Entry`.`party` = "{customer}"
                OR `tabPayment Entry`.`party` = "{customer}")
        ORDER BY `tabGL Entry`.`posting_date` ASC;
    """.format(accounts="\", \"".join(accounts), customer=customer, 
        currency_selector=currency_selector)
    
    data = frappe.db.sql(sql_query, as_dict=True)
    
    # add balance
    balance = 0
    for d in data:
        balance += d['amount']
        d['balance'] = balance
        
    return data
    
