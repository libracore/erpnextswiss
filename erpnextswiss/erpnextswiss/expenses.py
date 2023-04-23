# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore, Fink Zeitsysteme and contributors
# For license information, please see license.txt
#

# imports
from __future__ import unicode_literals
import frappe
from frappe import _

# this function will create the pretax deduction journal entry
@frappe.whitelist()
def expense_pretax(expense_claim, pretax_account):
    # get expense claim
    exp = frappe.get_doc("Expense Claim", expense_claim)
    accounts = []
    total_pretax = 0.0
    # collect expense deductions from pretax
    for expense in exp.expenses:
        if expense.vorsteuer > 0:
            accounts.append({
                'account': expense.default_account,
                'credit_in_account_currency': expense.vorsteuer
            })
            total_pretax += expense.vorsteuer
    # add pretax
    accounts.append({
        'account': pretax_account,
        'debit_in_account_currency': total_pretax
    })
    # create new journal entry
    jv = frappe.get_doc({
        'doctype': 'Journal Entry',
        'posting_date': exp.posting_date,
        'company': exp.company,
        'accounts': accounts,
        'cheque_no': exp.name,
        'cheque_date': exp.posting_date,
        'user_remark': "Pretax on expanse claim {0}".format(exp.name) 
    })
    # insert journal entry
    new_jv = jv.insert()
    new_jv.submit()
    # link journal entry to expense claim
    exp.pretax_record = new_jv.name
    exp.save()
    frappe.db.commit()
    return new_jv

@frappe.whitelist()
def expense_pretax_various(expense_claim):
    # get expense claim
    exp = frappe.get_doc("Expense Claim", expense_claim)
    accounts = []
    # collect expense deductions from pretax
    for expense in exp.expenses:
        if expense.vorsteuer > 0:
            accounts.append({
                'account': expense.default_account,
                'credit_in_account_currency': expense.vorsteuer,
                'cost_center': exp.cost_center
            })
            accounts.append({
                'account': expense.vat_account_head,
                'debit_in_account_currency': expense.vorsteuer,
                'cost_center': exp.cost_center
            })
    # only create journal entry if there are accounts
    if len(accounts) == 0:
        return None
    # create new journal entry
    jv = frappe.get_doc({
        'doctype': 'Journal Entry',
        'posting_date': exp.posting_date,
        'company': exp.company,
        'accounts': accounts,
        'cheque_no': exp.name,
        'cheque_date': exp.posting_date,
        'user_remark': "Pretax on expanse claim {0}".format(exp.name) 
    })
    # insert journal entry
    new_jv = jv.insert()
    new_jv.submit()
    # link journal entry to expense claim
    exp.pretax_record = new_jv.name
    exp.save()
    frappe.db.commit()
    return new_jv
    
# use this to revert a journal entry in case of cancellation of the expense claim
@frappe.whitelist()
def cancel_pretax(expense_claim):
    # get expense claim
    exp = frappe.get_doc("Expense Claim", expense_claim)
    # get journal entry
    jv = frappe.get_doc("Journal Entry", exp.pretax_record)
    # unlink
    exp.pretax_record = ""
    exp.save()
    # cancel
    jv.cancel()
    frappe.db.commit()
    return jv.name
