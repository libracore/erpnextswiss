# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
import time

class PaymentProposal(Document):
    def on_submit(self):
        # clean payments (to prevent accumulation on re-submit)
        self.payments = {}
        # create the aggregated payment table
        # collect customers
        suppliers = []
        for purchase_invoice in self.purchase_invoices:
            if purchase_invoice.supplier not in suppliers:
                suppliers.append(purchase_invoice.supplier)
        # aggregate sales invoices
        for supplier in suppliers:
            amount = 0
            references = []
            currency = ""
            address = ""
            # try executing in 30 days (will be reduced by actual due dates)
            exec_date = self.date + timedelta(days=30)
            for purchase_invoice in self.purchase_invoices:
                if purchase_invoice.supplier == supplier:
                    currency = purchase_invoice.currency
                    address = purchase_invoice.supplier_address
                    references.append(purchase_invoice.sales_invoice)
                    # find if skonto applies
                    if (purchase_invoice.skonto_date) and (purchase_invoice.skonto_date > datetime.now()):
						amount += purchase_invoice.skonto_amount
						if exec_date > purchase_invoice.skonto_date:
							exec_date > purchase_invoice.skonto_date					 
					else:
						amount += purchase_invoice.amount
						if exec_date > purchase_invoice.due_date:
							exec_date > purchase_invoice.due_date
                    # mark sales invoices as proposed
                    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    invoice.is_proposed = 1
                    invoice.save()
            # make sure execution date is valid
            if exec_date <= datetime.now():
				exec_date = datetime.now() + timedelta(days=1)
            # add new payment record
            new_payment = self.append('payments', {})
            supl = frappe.get_doc("Supplier", supplier)
            new_payment.receiver = supl.supplier_name
            new_pamyent.iban = supl.iban
			addr = frappe.get_doc("Address", address)
			new_payment.receiver_address_line1 = format(addr.address_line1)
			new_payment.receiver_address_line2 = "{0} {1}".format(addr.pincode, addr.city)
            new_payment.amount = amount
            new_payment.currency = currency
            new_payment.reference = " ".join(references)
            new_payment.execution_date = exec_date
            
        # collect employees
        employees = []
        for expense_claim in self.expense_claims:
            if expense_claim.employee not in employees:
                employees.append(expense_claim.employee)
        # aggregate expense claims
        for employee in employees:
            amount = 0
            references = []
            currency = ""
            for expense_claim in self.expense_claims:
                if expense_claim.employee == employee:
                    amount += expense_claim.amount
                    currency = expense_claim.currency
                    references.append(expense_claim.expense_claim)
                    # mark expense claim as proposed
                    invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
                    invoice.is_proposed = 1
                    invoice.save()
            # add new payment record
            new_payment = self.append('payments', {})
            emp = frappe.get_doc("Employee", employee)
            new_payment.receiver = emp.full_name
            new_pamyent.iban = emp.bank_ac_no
            try:
				address_lines = emp.permanent_address.split("\n")
				new_payment.receiver_address_line1 = address_lines[0]
				new_payment.receiver_address_line2 = address_lines[1]
			except:
				frappe.throw( _("Employee address not valid"))
            new_payment.amount = amount
            new_payment.currency = currency
            new_payment.reference = " ".join(references)
            new_payment.execution_date = self.date
            
        # save
        self.save()
    
    def create_bank_file(self):
        # create xml header
        content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        # TODO
        
        return { 'content': content }
    pass

# this function will create a new payment proposal
@frappe.whitelist()
def create_payment_proposal():
    # get planning days
    planning_days = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'planning_days')
    # get all suppliers with open purchase invoices
    sql_query = ("""SELECT 
                  `tabPurchase Invoice`.`supplier` AS `supplier`, 
                  `tabPurchase Invoice`.`name` AS `name`,  
                  `tabPurchase Invoice`.`outstanding_amount` AS `outstanding_amount`, 
                  `tabPurchase Invoice`.`due_date` AS `due_date`, 
                  `tabPurchase Invoice`.`currency` AS `currency`,
                  (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)) AS `skonto_date`,
                  (((100 - `tabPayment Terms Template`.`skonto_percent`)/100) * `tabPurchase Invoice`.`outstanding_amount`) AS `skonto_amount`
                FROM `tabPurchase Invoice` 
                LEFT JOIN `tabPayment Terms Template` ON `tabPurchase Invoice`.`payment_terms_template` = `tabPayment Terms Template`.`name`
                WHERE `tabPurchase Invoice`.`docstatus` = 1 
                  AND `tabPurchase Invoice`.`outstanding_amount` > 0
                  AND ((`tabPurchase Invoice`.`due_date` <= DATE_ADD(CURDATE(), INTERVAL {planning_days} DAY)) 
                    OR ((DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)) <= DATE_ADD(CURDATE(), INTERVAL {planning_days} DAY)))
                  AND `tabPurchase Invoice`.`is_proposed` = 0;""".format(planning_days=planning_days))
    purchase_invoices = frappe.db.sql(sql_query, as_dict=True)
    # get all purchase invoices that pending
    invoices = []
    for invoice in purchase_invoices:
        new_invoice = { 
            'supplier': invoice.supplier,
            'purchase_invoice': invoice.name,
            'amount': invoice.outstanding_amount,
            'due_date': invoice.due_date,
            'currency': invoice.currency,
            'skonto_date': invoice.skonto_date,
            'skonot_amount': invoice.skonto_amount
        }
        invoices.append(new_invoice)
    # get all open expense claims
    sql_query = ("""SELECT `name`, 
                  `employee`, 
                  `total_sanctioned_amount` AS `amount`,
                  `payable_account` 
                FROM `tabExpense Claim`
                WHERE `docstatus` = 1 
                  AND `status` = "Unpaid" 
                  AND `is_proposed` = 0;""")
    expense_claims = frappe.db.sql(sql_query, as_dict=True)          
    # get all purchase invoices that pending
    expenses = []
    for expense in expense_claims:
        new_expense = { 
            'expense_claim': expense.name,
            'employee': expense.employee,
            'amount': expense.amount,
            'payable_account': expense.payable_account
        }
        expenses.append(new_expense)
    # create new record
    new_record = None
    now = datetime.now()
    date = now + timedelta(days=1)
    new_proposal = frappe.get_doc({
        'doctype': "Payment Proposal",
        'title': "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
        'date': "{year:04d}-{month:02d}-{day:02d}".format(year=date.year, month=date.month, day=date.day),
        'purchase_invoices': invoices,
        'expense_claims': expenses
    })
    proposal_record = new_proposal.insert()
    new_record = proposal_record.name
    frappe.db.commit()
    return new_record
