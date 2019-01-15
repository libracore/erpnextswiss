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
    # check auto submit
    auto_submit = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "payment_reminder_auto_submit")
    # get all customers with open sales invoices
    sql_query = ("""SELECT `customer` 
            FROM `tabSales Invoice` 
            WHERE `outstanding_amount` > 0 
              AND `docstatus` = 1
              AND (`due_date` < CURDATE())
              AND `enable_lsv` = 0
              AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()))
            GROUP BY `customer`;""")
    customers = frappe.db.sql(sql_query, as_dict=True)
    # get all sales invoices that are overdue
    if customers:
        # find maximum reminder level
        sql_query = ("""SELECT MAX(`reminder_level`) AS `max` FROM 1bd3e0294da19198.`tabERPNextSwiss Settings Payment Reminder Charge`;""")
        try:
            max_level = frappe.db.sql(sql_query, as_dict=True)[0]['max']
        except:
            max_level = 3
        for customer in customers:
            sql_query = ("""SELECT `name`, `due_date`, `posting_date`, `payment_reminder_level`, `grand_total`, `outstanding_amount` 
                    FROM `tabSales Invoice` 
                    WHERE `outstanding_amount` > 0 AND `customer` = '{0}'
                      AND `docstatus` = 1
                      AND `enable_lsv` = 0
                      AND (`due_date` < CURDATE())
                      AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()));""".format(customer.customer))
            open_invoices = frappe.db.sql(sql_query, as_dict=True)
            if open_invoices:
                now = datetime.now()
                invoices = []
                highest_level = 0
                total_before_charges = 0
                for invoice in open_invoices:
                    level = invoice.payment_reminder_level + 1
                    if level > max_level:
                        level = max_level
                    new_invoice = { 
                        'sales_invoice': invoice.name,
                        'amount': invoice.grand_total,
                        'outstanding_amount': invoice.outstanding_amount,
                        'posting_date': invoice.posting_date,
                        'due_date': invoice.due_date,
                        'reminder_level': level
                    }
                    if level > highest_level:
                        highest_level = level
                    total_before_charges += invoice.outstanding_amount
                    invoices.append(new_invoice)
                # find reminder charge
                charge_matches = frappe.get_all("ERPNextSwiss Settings Payment Reminder Charge", 
                    filters={ 'reminder_level': highest_level },
                    fields=['reminder_charge'])
                reminder_charge = 0
                if charge_matches:
                    reminder_charge = charge_matches[0]['reminder_charge']
                new_reminder = frappe.get_doc({
                    "doctype": "Payment Reminder",
                    "customer": customer.customer,
                    "date": "{year:04d}-{month:02d}-{day:02d}".format(
                        year=now.year, month=now.month, day=now.day),
                    "title": "{customer} {year:04d}-{month:02d}-{day:02d}".format(
                        customer=customer.customer, year=now.year, month=now.month, day=now.day),
                    "sales_invoices": invoices,
                    'highest_level': highest_level,
                    'total_before_charge': total_before_charges,
                    'reminder_charge': reminder_charge,
                    'total_with_charge': (total_before_charges + reminder_charge)
                })
                reminder_record = new_reminder.insert()
                if int(auto_submit) == 1:
                    reminder_record.update_reminder_levels()
                    reminder_record.submit()
                frappe.db.commit()
    return
