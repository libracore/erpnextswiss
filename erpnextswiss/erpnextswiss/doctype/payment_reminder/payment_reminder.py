# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
import json
from frappe.utils.data import add_days

class PaymentReminder(Document):
    # this will apply all payment reminder levels and blocking days (as exclude_from_payment_reminder_until) in the sales invoices
    def update_reminder_levels(self):
        blocking_days = get_blocking_days()
        for invoice in self.sales_invoices:
            sales_invoice = frappe.get_doc("Sales Invoice", invoice.sales_invoice)
            
            # apply reminder_level
            sales_invoice.payment_reminder_level = invoice.reminder_level
            
            # apply exclude_from_payment_reminder_until based on blocking days
            if len(get_blocking_days()) >= invoice.reminder_level:
                if blocking_days[str(invoice.reminder_level)] > 0:
                    exclude_from_payment_reminder_until = add_days(self.date, blocking_days[str(invoice.reminder_level)])
                    sales_invoice.exclude_from_payment_reminder_until = exclude_from_payment_reminder_until
            else:
                # e.g. if the reminder level is higher than 3 and no blocking days are recorded (default max reminder level is 3)
                sales_invoice.exclude_from_payment_reminder_until = None
            
            sales_invoice.save()
        return
    # apply payment reminder levels and blocking days on submit (server based)
    def on_submit(self):
        self.update_reminder_levels()
    pass

# this function will create new payment reminders
@frappe.whitelist()
def create_payment_reminders(company):
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
              AND `company` = "{company}"
            GROUP BY `customer`;""".format(company=company))
    customers = frappe.db.sql(sql_query, as_dict=True)
    # get all sales invoices that are overdue
    if customers:
        # find maximum reminder level
        sql_query = ("""SELECT MAX(`reminder_level`) AS `max` FROM `tabERPNextSwiss Settings Payment Reminder Charge`;""")
        try:
            max_level = frappe.db.sql(sql_query, as_dict=True)[0]['max']
            if not max_level:
                max_level = 3
        except:
            max_level = 3
        for customer in customers:
            sql_query = ("""SELECT 
                        `name`, 
                        `due_date`, 
                        `posting_date`, 
                        `payment_reminder_level`, 
                        `grand_total`, 
                        `outstanding_amount` , 
                        `currency`,
                        `contact_email`
                    FROM `tabSales Invoice` 
                    WHERE `outstanding_amount` > 0 AND `customer` = '{customer}'
                      AND `docstatus` = 1
                      AND `enable_lsv` = 0
                      AND (`due_date` < CURDATE())
                      AND `company` = "{company}"
                      AND ((`exclude_from_payment_reminder_until` IS NULL) OR (`exclude_from_payment_reminder_until` < CURDATE()));
                    """.format(customer=customer.customer, company=company))
            open_invoices = frappe.db.sql(sql_query, as_dict=True)
            email = None
            if open_invoices:
                now = datetime.now()
                invoices = []
                highest_level = 0
                total_before_charges = 0
                currency = None
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
                    currency = invoice.currency
                    if invoice.contact_email:
                        email = invoice.contact_email
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
                    'total_with_charge': (total_before_charges + reminder_charge),
                    'company': company,
                    'currency': currency,
                    'email': email
                })
                reminder_record = new_reminder.insert(ignore_permissions=True)
                if int(auto_submit) == 1:
                    reminder_record.update_reminder_levels()
                    reminder_record.submit()
                frappe.db.commit()
    return

# this allows to submit multiple payment reminders at once
@frappe.whitelist()
def bulk_submit(names):
    docnames = json.loads(names)
    for name in docnames:
        payment_reminder = frappe.get_doc("Payment Reminder", name)
        payment_reminder.update_reminder_levels()
        payment_reminder.submit()
    return

# returns an object of reminder_level vs blocking_days
def get_blocking_days():
    # find maximum reminder level
    sql_query = ("""SELECT MAX(`reminder_level`) AS `max` FROM `tabERPNextSwiss Settings Payment Reminder Level Blocking Period`""")
    try:
        max_level = frappe.db.sql(sql_query, as_dict=True)[0]['max']
        if not max_level:
            max_level = 3
    except:
        max_level = 3
    
    # create blocking_days dict
    blocking_days = {}
    for reminder_level in range(1, max_level + 1):
        blocking_days[str(reminder_level)] = frappe.db.get_value('ERPNextSwiss Settings Payment Reminder Level Blocking Period', {'reminder_level': reminder_level}, ['blocking_days']) or 0
    
    return blocking_days
