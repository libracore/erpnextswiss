# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DirectDebitProposal(Document):
	pass

# this function will create a new direct debit proposal
@frappe.whitelist()
def create_direct_debit_proposal():
    # get all customers with open sales invoices
    sql_query = ("""SELECT `customer`, `name`,  `outstanding_amount`, `due_date`
            FROM `tabSales Invoice` 
            WHERE `docstatus` = 1 
              AND `outstanding_amount` > 0
              AND `enable_lsv` = 1
              AND `is_proposed` = 0;""")
    sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    new_record = None
    # get all sales invoices that are overdue
    if sales_invoices:
        now = datetime.now()
        invoices = []
        for invoice in sales_invoices:
            new_invoice = { 
                'customer': invoice.customer,
                'sales_invoice': invoice.name,
                'amount': invoice.outstanding_amount,
                'due_date': invoice.due_date
            }
            invoices.append(new_invoice)
        # create new record
        new_proposal = frappe.get_doc({
            "doctype": "Direct Debit Proposal",
            "title": "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
            "date": "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
            "payments": invoices
        })
        proposal_record = new_proposal.insert()
        new_record = proposal_record.name
        frappe.db.commit()
    return new_record
