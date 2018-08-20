# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from erpnextswiss.erpnextswiss.page.bankimport.bankimport import create_reference

@frappe.whitelist()
def get_open_sales_invoices():
    # get unpaid sales invoices
    sql_query = ("""SELECT `name`, `customer`, `base_grand_total`, `outstanding_amount`, `due_date`, `esr_reference` 
                FROM `tabSales Invoice` 
                WHERE `docstatus` = 1 AND `outstanding_amount` > 0 
                ORDER BY `due_date` ASC""")
    unpaid_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    return {'unpaid_sales_invoices': unpaid_sales_invoices }

@frappe.whitelist()
def get_unallocated_payment_entries():
    # get unallocated payment entries
    sql_query = ("""SELECT `name`, `party`, `paid_amount`, `posting_date`, `remarks` 
                FROM `tabPayment Entry` 
                WHERE `docstatus` = 0  
                  AND `payment_type` = 'Receive' 
                ORDER BY `posting_date` ASC""")
    unallocated_payment_entries = frappe.db.sql(sql_query, as_dict=True)
    return {'unallocated_payment_entries': unallocated_payment_entries }

@frappe.whitelist()
def match(sales_invoice, payment_entry):
    # get the customer
    customer = frappe.get_value("Sales Invoice", sales_invoice, "customer")
    if customer:
        payment_entry_record = frappe.get_doc("Payment Entry", payment_entry)
        if payment_entry:
            # assign the actual customer
            payment_entry_record.party = customer            
            payment_entry_record.save()
            
            # now, add the reference to the sales invoice
            create_reference(payment_entry, sales_invoice)
            
            # and finally submit the payment entry (direct submit will void the reference :-( )
            #payment_entry_record.submit()
            
            return { 'payment_entry': payment_entry_record.name }
        else:
            return { 'error': "Payment entry not found" }
    else:
        return { 'error': "Customer not found" }
 
@frappe.whitelist()
def submit(payment_entry):
    payment_entry_record = frappe.get_doc("Payment Entry", payment_entry)
    payment_entry_record.submit()
    return { 'message': "Done" }

@frappe.whitelist()
def submit_all(payment_entries):
    # get the array from the string parameter
    payments = eval(payment_entries)
    # loop through all matched payments and submit them
    for payment_entry in payments:
        submit(payment_entry)
    return { 'message': "Done" }

@frappe.whitelist()
def auto_match(method="docid"):
    # make method lower case
    method = method.lower()
    # prepare array of matched payments
    matched_payments = []
    # read all new payments
    new_payments = get_unallocated_payment_entries()['unallocated_payment_entries']
    # loop through all unpaid sales invoices
    pending_sales_invoices = get_open_sales_invoices()['unpaid_sales_invoices']
    for unpaid_sales_invoice in pending_sales_invoices:
        if method == "docid":
            for payment in new_payments:
                if unpaid_sales_invoice['name'] in payment['remarks']:
                    matched_payment_entry = match(unpaid_sales_invoice['name'], payment['name'])['payment_entry']
                    matched_payments.append(matched_payment_entry)
        elif method == "esr":
            # only check Sales Invoice records with an ESR reference
            if unpaid_sales_invoice['esr_reference']:
                for payment in new_payments:
                    if unpaid_sales_invoice['esr_reference'].replace(' ', '') in payment['remarks']:
                        matched_payment_entry = match(unpaid_sales_invoice['name'], payment['name'])['payment_entry']
                        matched_payments.append(matched_payment_entry)
    return { 'message': "Done", 'payments': matched_payments }
