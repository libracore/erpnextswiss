# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from erpnextswiss.erpnextswiss.page.bankimport.bankimport import create_reference

@frappe.whitelist()
def get_open_sales_invoices():
    # get unpaid sales invoices
    sql_query = ("SELECT `name`, `customer`, `base_grand_total`, `due_date` " +
                "FROM `tabSales Invoice` " +
                "WHERE `docstatus` = 1 " + 
                "AND `status` != 'Paid'")
    unpaid_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    return {'unpaid_sales_invoices': unpaid_sales_invoices }

@frappe.whitelist()
def get_unallocated_payment_entries():
    # get unallocated payment entries
    sql_query = ("SELECT `name`, `party`, `paid_amount`, `posting_date`, `remarks` " +
                "FROM `tabPayment Entry` " +
                "WHERE `docstatus` = 0 " + 
                "AND `payment_type` = 'Receive'")
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
