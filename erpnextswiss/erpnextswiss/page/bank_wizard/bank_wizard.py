# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import hashlib
import json
from bs4 import BeautifulSoup
      
# this function tries to match the amount to an open sales invoice
#
# returns the sales invoice reference (name string) or None
def match_by_amount(amount):
    # get sales invoices
    sql_query = ("SELECT `name` " +
                "FROM `tabSales Invoice` " +
                "WHERE `docstatus` = 1 " + 
                "AND `grand_total` = {0} ".format(amount) + 
                "AND `status` != 'Paid'")
    open_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    if open_sales_invoices:
        if len(open_sales_invoices) == 1:
            # found exactly one match
            return open_sales_invoices[0].name
        else:
            # multiple sales invoices with this amount found
            return None
    else:
        # no open sales invoice with this amount found
        return None
        
# this function tries to match the comments to an open sales invoice
# 
# returns the sales invoice reference (name sting) or None
def match_by_comment(comment):
    # get sales invoices (submitted, not paid)
    sql_query = ("SELECT `name` " +
                "FROM `tabSales Invoice` " +
                "WHERE `docstatus` = 1 " + 
                "AND `status` != 'Paid'")
    open_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    if open_sales_invoices:
        # find sales invoice referernce in the comment
        for reference in open_sales_invoices.name:
            if reference in comment:
                # found a match
                return reference
    return None

# find unpaid invoices for a customer
#
# returns a dict (name) of sales invoice references or None
def get_unpaid_sales_invoices_by_customer(customer):
    # get sales invoices (submitted, not paid)
    sql_query = ("SELECT `name` " +
                "FROM `tabSales Invoice` " +
                "WHERE `docstatus` = 1 " + 
                "AND `customer` = '{0}' ".format(customer) +
                "AND `status` != 'Paid'")
    open_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    return open_sales_invoices   

# create a payment entry
def create_payment_entry(date, to_account, received_amount, transaction_id, remarks, auto_submit=False):
    # get default customer
    default_customer = get_default_customer()
    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
        # create new payment entry
        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
        new_payment_entry.payment_type = "Receive"
        new_payment_entry.party_type = "Customer";
        new_payment_entry.party = default_customer
        # date is in DD.MM.YYYY
        new_payment_entry.posting_date = date
        new_payment_entry.paid_to = to_account
        new_payment_entry.received_amount = received_amount
        new_payment_entry.paid_amount = received_amount
        new_payment_entry.reference_no = transaction_id
        new_payment_entry.reference_date = date
        new_payment_entry.remarks = remarks
        inserted_payment_entry = new_payment_entry.insert()
        if auto_submit:
            new_payment_entry.submit()
        frappe.db.commit()
        return inserted_payment_entry
    else:
        return None
    
# creates the reference record in a payment entry
def create_reference(payment_entry, sales_invoice):
    # create a new payment entry reference
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry.parent = payment_entry
    reference_entry.parentfield = "references"
    reference_entry.parenttype = "Payment Entry"
    reference_entry.reference_doctype = "Sales Invoice"
    reference_entry.reference_name = sales_invoice
    reference_entry.total_amount = frappe.get_value("Sales Invoice", sales_invoice, "base_grand_total")
    reference_entry.outstanding_amount = frappe.get_value("Sales Invoice", sales_invoice, "outstanding_amount")
    paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
    if paid_amount > reference_entry.outstanding_amount:
        reference_entry.allocated_amount = reference_entry.outstanding_amount
    else:
        reference_entry.allocated_amount = paid_amount
    reference_entry.insert();
    return
    
def log(comment):
	new_comment = frappe.get_doc({"doctype": "Log"})
	new_comment.comment = comment
	new_comment.insert()
	return new_comment

# converts a parameter to a bool
def assert_bool(param):
    result = param
    if result == 'false':
        result = False
    elif result == 'true':
        result = True	 
    return result  

def get_default_customer():
    default_customer = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "default_customer")
    if not default_customer:
        default_customer = "Guest"
    return default_customer

@frappe.whitelist()
def get_bank_accounts():
    accounts = frappe.get_list('Account', filters={'account_type': 'Bank', 'is_group': 0}, fields=['name'])
    selectable_accounts = []
    for account in accounts:
		selectable_accounts.append(account.name)    
    
    # frappe.throw(selectable_accounts)
    return {'accounts': selectable_accounts }

@frappe.whitelist()
def read_camt053(content, bank, account, auto_submit=False):
    #read_camt_transactions_re(content)
    soup = BeautifulSoup(content, 'lxml')
    
    # general information
    try:
        #iban = doc['Document']['BkToCstmrStmt']['Stmt']['Acct']['Id']['IBAN']
        iban = soup.document.bktocstmrstmt.stmt.acct.id.iban.get_text()
    except:
        # node not found, probably wrong format
        return { "message": _("Unable to read structure. Please make sure that you have selected the correct format."), "records": None }
            
    # transactions
    #new_payment_entries = read_camt_transactions(doc['Document']['BkToCstmrStmt']['Stmt']['Ntry'], bank, account, auto_submit)
    entries = soup.find_all('ntry')
    new_payment_entries = read_camt_transactions(entries, bank, account, auto_submit)
    
    message = _("Successfully imported {0} payments.".format(len(new_payment_entries)))
    
    return { "message": message, "records": new_payment_entries } 
