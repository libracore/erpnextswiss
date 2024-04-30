# -*- coding: utf-8 -*-
# Copyright (c) 2018-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_manager import save_file, remove_all
from erpnext.setup.utils import get_exchange_rate as get_core_exchange_rate
from frappe.utils import rounded

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
            `tabGL Entry`.`voucher_no` AS `voucher_no`,
            `tabGL Entry`.`voucher_type` AS `voucher_type`
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
    
@frappe.whitelist()
def get_exchange_rate(from_currency=None, to_currency=None, company=None, date=None):
    if not from_currency and company:
        from_currency = frappe.get_cached_value("Company", company, "default_currency")
    if not to_currency and company:
        to_currency = frappe.get_cached_value("Company", company, "default_currency")
    
    return get_core_exchange_rate(from_currency=from_currency, 
        to_currency=to_currency, transaction_date=date)
        
def get_debit_accounts(company):
    accounts = []
    for a in frappe.get_all("Account", filters={'account_type': 'Receivable', 'disabled': 0, 'company': company}, fields=['name']):
        accounts.append(a.get("name"))
    return accounts

"""
This function will combine a split booking into booking pairs of debit/credit
"""
def get_booking_pairs(voucher_type, voucher_no):
    # get bookings
    gl_entries = frappe.db.sql("""
        SELECT
            `name`,
            `account`,
            `debit`,
            `debit_in_account_currency`,
            `credit`,
            `credit_in_account_currency`
        FROM `tabGL Entry`
        WHERE `voucher_type` = "{voucher_type}" AND `voucher_no` = "{voucher_no}"
        ORDER BY `debit` DESC, `credit` ASC;
        """.format(voucher_type=voucher_type, voucher_no=voucher_no), as_dict=True)
        
    # verify totals
    totals = {
        'total_debit': 0,
        'total_credit': 0
    }
    for g in gl_entries:
        totals['total_debit'] += g['debit']
        totals['total_credit'] += g['credit']
    if rounded(totals['total_debit'], 2) != rounded(totals['total_credit'], 2):
        frappe.throw( _("Debit and credit not equal in {0}").format(voucher_no), _("Total validation failed") )
        
    # allocated debit to credit and build pairs
    booking_pairs = {}
    for d in gl_entries:
        if not d['debit'] and not d['credit']:
            exchange_rate = 1
        else:
            exchange_rate = d['debit_in_account_currency'] / d['debit'] if d['debit'] else d['credit_in_account_currency'] / d['credit']
        for c in range((len(gl_entries) - 1), (-1), -1):
            if d['debit'] == 0:
                # this debit is allocated
                continue
            else:
                # extend exchange rate
                if exchange_rate == 1:
                    if not gl_entries[c]['debit'] and not gl_entries[c]['credit']:
                        exchange_rate = 1
                    else:
                        exchange_rate = gl_entries[c]['debit_in_account_currency'] / gl_entries[c]['debit'] if gl_entries[c]['debit'] else gl_entries[c]['credit_in_account_currency'] / gl_entries[c]['credit']
                key = "{0}|{1}".format(d['account'], gl_entries[c]['account'])
                if key not in booking_pairs:
                    booking_pairs[key] = {
                        'amount': 0, 
                        'exchange_rate': exchange_rate,
                        'debit_account': d['account'],
                        'credit_account': gl_entries[c]['account']
                    }
                if d['debit'] <= gl_entries[c]['credit']:
                    # completely allocate debit
                    booking_pairs[key]['amount'] += d['debit']
                    d['debit'] = 0
                    gl_entries[c]['credit'] -= d['debit']
                else:
                    # partially allocate debit with complete credit
                    booking_pairs[key]['amount'] += gl_entries[c]['credit']
                    d['debit'] -= gl_entries[c]['credit']
                    gl_entries[c]['credit'] = 0
    
    # round 
    for k, v in booking_pairs.items():
        booking_pairs[k]['amount'] = rounded(v['amount'], 2)
        booking_pairs[k]['foreign_amount'] = rounded((v['exchange_rate'] * v['amount']), 2)
    
    return booking_pairs
    
