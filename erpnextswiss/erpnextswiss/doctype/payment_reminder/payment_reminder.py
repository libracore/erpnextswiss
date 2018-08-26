# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime

class PaymentReminder(Document):
    # this will apply all payment reminder levels in the sales invoices
    def update_reminder_levels(self):
        for invoice in self.sales_invoices:
            sales_invoice = frappe.get_doc("Sales Invoice", invoice.sales_invoice)
            sales_invoice.payment_reminder_level = invoice.reminder_level
            sales_invoice.save()
        return
    pass

# this function will create new payment reminders
@frappe.whitelist()
def create_payment_reminders():
    # get all customers with open sales invoices
    sql_query = ("""SELECT `customer` 
            FROM `tabSales Invoice` 
            WHERE `outstanding_amount` > 0 
              AND `docstatus` = 1
              AND (`due_date` < CURDATE())
              AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()))
            GROUP BY `customer`;""")
    customers = frappe.db.sql(sql_query, as_dict=True)
    # get all sales invoices that are overdue
    if customers:
        for customer in customers:
            sql_query = ("""SELECT `name`, `due_date`, `payment_reminder_level`, `grand_total` 
                    FROM `tabSales Invoice` 
                    WHERE `outstanding_amount` > 0 AND `customer` = '{0}'
                      AND `docstatus` = 1
                      AND (`due_date` < CURDATE())
                      AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()));""".format(customer.customer))
            open_invoices = frappe.db.sql(sql_query, as_dict=True)
            if open_invoices:
                now = datetime.now()
                invoices = []
                for invoice in open_invoices:
                    new_invoice = { 
                        'sales_invoice': invoice.name,
                        'amount': invoice.grand_total,
                        'due_date': invoice.due_date,
                        'reminder_level': invoice.payment_reminder_level + 1
                    }
                    invoices.append(new_invoice)
                new_reminder = frappe.get_doc({
                    "doctype": "Payment Reminder",
                    "customer": customer.customer,
                    "date": "{0}-{1}-{2}".format(now.year, now.month, now.day),
                    "title": "{0} {1}-{2}-{3}".format(customer.customer, now.year, now.month, now.day),
                    "sales_invoices": invoices
                })
                new_reminder.insert()
                frappe.db.commit()
    return
