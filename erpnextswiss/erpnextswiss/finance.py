# -*- coding: utf-8 -*-
# Copyright (c) 2018-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _

""" Jinja hook to create account sheets """
def get_account_sheets(fiscal_year):
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    _opening_debit = 0
    _opening_credit = 0
    account_data = []
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
            if account.report_type == "Balance Sheet":
                # compute opening balance
                opening_transactions = frappe.get_all("GL Entry", filters=[
                  ['account', '=', account.name],
                  ['posting_date', '<', fy.year_start_date]
                ], fields=['debit', 'credit'])    
                # reset counters
                _opening_debit = 0
                _opening_credit = 0  
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
            # loop through transactions
            for transaction in transactions:
                # update current debit/credit
                if account.report_type == "Balance Sheet":
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
            # compute closing balance
            if _opening_debit > _opening_credit:
                _delta = _opening_debit - _opening_credit
                _opening_debit = _delta
                _opening_credit = 0
            else:
                _delta = _opening_credit - _opening_debit
                _opening_debit = 0
                _opening_credit = _delta
            _data['closing_debit'] = _opening_debit
            _data['closing_credit'] = _opening_credit
            _data['closing_balance'] = _balance
            # append data to storage
            account_data.append(_data)
    return account_data
