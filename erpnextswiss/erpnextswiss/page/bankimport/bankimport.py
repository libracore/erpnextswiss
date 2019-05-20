# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import hashlib
from bs4 import BeautifulSoup
import json
from datetime import datetime
import operator
import re
import six

def parse_ubs(content, account, auto_submit=False):
    # parse a ubs bank extract csv
    # collect all lines of the file
    #log("Starting parser...")
    lines = content.split("\n")
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
        for i in range(1, len(lines)):
            #log("Reading {0} of {1} lines...".format(i, len(lines)))
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].split(';')
           
            # get received amount, only continue if this has a value
            if len(fields) > 19:
                received_amount = fields[19]
                #log("Received amount {0} ({1}, {2})".format(received_amount, fields[18], fields[20]))
                if received_amount != "":
                    # get unique transaction ID
                    transaction_id = fields[15]
                    #log("Checking transaction {0}".format(transaction_id))
                    # cross-check if this transaction was already recorded
                    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                        #log("Adding transaction {0}".format(transaction_id))
                        # create new payment entry
                        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                        new_payment_entry.payment_type = "Receive"
                        new_payment_entry.party_type = "Customer";
                        # get the customer name
                        customer_name = fields[13]
                        customer = frappe.get_value('Customer', customer_name, 'name')
                        if customer:
                            new_payment_entry.party = customer
                        else:
                            new_payment_entry.party = default_customer
                        # date is in DD.MM.YYYY
                        date = convert_to_unc(fields[11])
                        new_payment_entry.posting_date = date
                        new_payment_entry.paid_to = account
                        # remove thousands separator
                        received_amount = received_amount.replace("'", "")
                        new_payment_entry.received_amount = float(received_amount)
                        new_payment_entry.paid_amount = float(received_amount)
                        new_payment_entry.reference_no = transaction_id
                        new_payment_entry.reference_date = date
                        new_payment_entry.remarks = fields[13] + ", " + fields[14]
                        inserted_payment_entry = new_payment_entry.insert()
                        if auto_submit:
                            new_payment_entry.submit()
                        new_payment_entries.append(inserted_payment_entry.name)
        
        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )

def parse_zkb(content, account, auto_submit=False):
    # parse a zkb bank extract csv
    # remove the quotation marks and collect all lines of the file
    #log("Starting parser...")
    lines = content.replace("\"", "").split("\n")
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
    #if True:
        for i in range(1, len(lines)):
            #log("Reading {0} of {1} lines...".format(i, len(lines)))
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].split(';')
            #frappe.log_error("Reading {0} of {1} lines... ({2} fields)".format(i, len(lines), len(fields)))
           
            # get received amount, only continue if this has a value
            if len(fields) > 10:
                received_amount = fields[7]
                #log("Received amount {0} ({1}, {2})".format(received_amount, fields[18], fields[20]))
                #frappe.log_error("Received amount {0} ({1})".format(received_amount, fields[4]))
                if received_amount != "":
                    # get unique transaction ID
                    transaction_id = fields[4]
                    #log("Checking transaction {0}".format(transaction_id))
                    #frappe.log_error("Checking transaction {0}".format(transaction_id))
                    # cross-check if this transaction was already recorded
                    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                        #log("Adding transaction {0}".format(transaction_id))
                        # create new payment entry
                        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                        new_payment_entry.payment_type = "Receive"
                        new_payment_entry.party_type = "Customer";
                        # get the customer name
                        description = fields[1].split(":")
                        #frappe.throw("Description" + fields[1] + " Amount " + fields[7])
                        try:
                            long_customer_text = description[1].split(",")
                        except:
                            long_customer_text = "not defined"
                        customer_name = long_customer_text[0].strip()
                        customer = frappe.get_value('Customer', customer_name, 'name')
                        if customer:
                            new_payment_entry.party = customer
                        else:
                            new_payment_entry.party = default_customer
                        # date is in DD.MM.YYYY
                        date = convert_to_unc(fields[8])
                        new_payment_entry.posting_date = date
                        new_payment_entry.paid_to = account
                        # remove thousands separator
                        received_amount = received_amount.replace("'", "")
                        new_payment_entry.received_amount = float(received_amount)
                        new_payment_entry.paid_amount = float(received_amount)
                        new_payment_entry.reference_no = transaction_id
                        new_payment_entry.reference_date = date
                        if (i + 1) < len(lines):
                            fields_next_row = lines[i + 1].split(';')
                            new_payment_entry.remarks = fields_next_row[1] + u", " + fields_next_row[10]
                        #frappe.log_error("New payment: {0}, {1}".format(transaction_id, date))
                        inserted_payment_entry = new_payment_entry.insert()
                        if auto_submit:
                            new_payment_entry.submit()
                        new_payment_entries.append(inserted_payment_entry.name)
        
        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )

def parse_raiffeisen(content, account, auto_submit=False):
    # parse a raiffeisen bank extract csv
    #
    # Column definition:
    # IBAN (0), Booket At (1), Text (2), Credit/Debit Amount (3), Balance (4), Valuta Date (5)
    #
    IBAN = 0
    BOOKED_AT = 1
    TEXT = 2
    AMOUNT = 3
    BALANCE = 4
    VALUTA_DATE = 5
    # cell separator: ;
    # collect all lines of the file
    #log("Starting parser...")
    lines = content.split("\n")
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
    #if True: # this is for detailed debug messages ;-)
        for i in range(1, len(lines)):
            #log("Reading {0} of {1} lines...".format(i, len(lines)))
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].split(';')
            # get received amount, only continue if this has a POSITIVE value
            if len(fields) > 5:
                if fields[AMOUNT] != "":
                    # skip second lines (additional data for payments)
                    received_amount = float(fields[AMOUNT])
                    #log("Received amount {0}".format(received_amount))
                    if received_amount > 0:
                        # get unique transaction ID
                        uniquestr = "{0}:{1}:{2}".format(fields[BOOKED_AT], fields[AMOUNT], fields[BALANCE])
                        transaction_id = hashlib.md5(uniquestr.encode('utf-8')).hexdigest()
                        try:
                            nextline_fields = lines[i+1].split(';')
                            if nextline_fields[AMOUNT] == "":
                                # containes the end-to-end reference
                                remarks = nextline_fields[TEXT]
                            else:
                                remarks = None
                        except:
                            remarks = None
                        
                        #log("Checking transaction {0}".format(transaction_id))
                        # cross-check if this transaction was already recorded
                        if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                            #log("Adding transaction {0}".format(transaction_id))
                            # create new payment entry
                            new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                            new_payment_entry.payment_type = "Receive"
                            new_payment_entry.party_type = "Customer";
                            # get the customer name (TEXT is "Gutschrift [customer]" on debits)
                            description = fields[TEXT].split(" ")
                            customer_name = " ".join(description[1:])
                            customer = frappe.get_value('Customer', customer_name, 'name')
                            if customer:
                                new_payment_entry.party = customer
                            else:
                                new_payment_entry.party = default_customer
                            # date is in "DD.MM.YYYY hh.mm" or "YYYY-MM-DD hh:mm" (bug #11)
                            date_time = fields[BOOKED_AT].split(' ')
                            date = convert_to_unc(date_time[0])
                            new_payment_entry.posting_date = date
                            new_payment_entry.paid_to = account
                            # remove thousands separator
                            new_payment_entry.received_amount = float(received_amount)
                            new_payment_entry.paid_amount = float(received_amount)
                            new_payment_entry.reference_no = transaction_id
                            new_payment_entry.reference_date = date
                            if (i + 1) < len(lines):
                                new_payment_entry.remarks = "{0} {1}".format(fields[TEXT], (remarks or ""))
                            inserted_payment_entry = new_payment_entry.insert()
                            if auto_submit:
                                new_payment_entry.submit()
                            new_payment_entries.append(inserted_payment_entry.name)
        
        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )
        
def parse_cs(content, account, auto_submit=False):
    # parse a credit suisse bank extract csv
    # collect all lines of the file
    lines = content.split("\n")
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
        for i in range(1, len(lines)):
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].split(';')
           
            # get received amount, only continue if this has a value
            if len(fields) > 5:
                received_amount = fields[3]
                if received_amount != "":
                    # get unique transaction ID
                    transaction_id = fields[0] + fields[1]
                    # cross-check if this transaction was already recorded
                    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                        # create new payment entry
                        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                        new_payment_entry.payment_type = "Receive"
                        new_payment_entry.party_type = "Customer";
                        # get the customer name
                        description = fields[1].split(",")
                        customer_name = description[1].strip()
                        customer = frappe.get_value('Customer', customer_name, 'name')
                        if customer:
                            new_payment_entry.party = customer
                        else:
                            new_payment_entry.party = default_customer
                        # date is in DD.MM.YYYY
                        date = convert_to_unc(fields[4])
                        new_payment_entry.posting_date =  date
                        new_payment_entry.paid_to = account
                        # remove thousands separator
                        received_amount = received_amount.replace("'", "")
                        new_payment_entry.received_amount = float(received_amount)
                        new_payment_entry.paid_amount = float(received_amount)
                        new_payment_entry.reference_no = transaction_id
                        new_payment_entry.reference_date = date
                        new_payment_entry.remarks = fields[1]
                        inserted_payment_entry = new_payment_entry.insert()
                        if auto_submit:
                            new_payment_entry.submit()
                        new_payment_entries.append(inserted_payment_entry.name)
        
        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )

def parse_migrosbank(content, account, auto_submit=False):
    # parse a migrosbank bank extract csv
    # collect all lines of the file
    lines = content.split("\n")
    
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
        for i in range(12, len(lines)):
            # skip line 0..11, it contains account information the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].split(';')
            
            # get received amount, only continue if this has a value
            if len(fields) > 3:
                received_amount = float(fields[2])
                # is a received payment if the amount is bigger than 0
                if received_amount > 0:
                    # get unique transaction ID
                    transaction_id = lines[i]
                    # cross-check if this transaction was already recorded
                    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                        # create new payment entry
                        new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                        new_payment_entry.payment_type = "Receive"
                        new_payment_entry.party_type = "Customer";
                        new_payment_entry.party = default_customer
                        # date is in DD.MM.YYYY
                        date = convert_to_unc(fields[0])
                        new_payment_entry.posting_date = date
                        new_payment_entry.paid_to = account
                        new_payment_entry.received_amount = received_amount
                        new_payment_entry.paid_amount = received_amount
                        new_payment_entry.reference_no = transaction_id
                        new_payment_entry.reference_date = date
                        new_payment_entry.remarks = lines[i]
                        inserted_payment_entry = new_payment_entry.insert()
                        if auto_submit:
                            new_payment_entry.submit()
                        new_payment_entries.append(inserted_payment_entry.name)
        
        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )

def parse_voba(content, account, auto_submit=False):
    # parse a volksbank bank extract csv
    #
    # Column definition:
    # Buchungstag (0), Valuta(1), Auftraggeber/Zahlungsempfänger(2), Empfänger/Zahlungspflichtiger(3),
    # Konto-Nr. (4), IBAN (5),BLZ (6) BIC (7), Vorgang/Verwendungszweck (8),
    # Kundenreferenz (9),Währung (10), Umsatz (11), "N/A Typ"(12)
    #
    BOOKED_AT = 0
    VALUTA = 1
    SENDER = 2
    RECEIVER = 3
    IBAN = 5
    BIC = 7
    AMOUNT = 11
    AMOUNTTYPE = 12
    # AMOUNTRYPE: S = negative; H = possitive

    # cell separator: ;
    # collect all lines of the file
    #log("Starting parser...")
    lines = content.split("\r\n")
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
    # if True: # this is for detailed debug messages ;-)
        for i in range(13, len(lines) - 4):
            #log("Reading {0} of {1} lines...".format(i, len(lines)))
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].replace("\n","~").replace('"',"").split(';')
            # get received amount, only continue if this has a POSITIVE value
            if len(fields) > 12:
                if fields[AMOUNT] != "":
                    # skip second lines (additional data for payments)
                    received_amount = float(fields[AMOUNT].replace(".","").replace(",","."))
                    #log("Received amount {0}".format(received_amount))
                    if fields[AMOUNTTYPE] == "H":
                        if received_amount > 0:
                            # get unique transaction ID
                            transaction_id = hashlib.md5("{0}:{1}:{2}".format(fields[BOOKED_AT], fields[AMOUNT], fields[SENDER])).hexdigest()
                            #log("Checking transaction {0}".format(transaction_id))
                            # cross-check if this transaction was already recorded
                            if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                                #log("Adding transaction {0}".format(transaction_id))
                                # create new payment entry
                                new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                                new_payment_entry.payment_type = "Receive"
                                new_payment_entry.party_type = "Customer";
                                # get the customer name
                                customer_name = fields[SENDER]
                                customer = frappe.get_value('Customer', customer_name, 'name')
                                if customer:
                                    new_payment_entry.party = customer
                                else:
                                    new_payment_entry.party = default_customer
                                # date is in "DD.MM.YYYY hh.mm" or "YYYY-MM-DD hh:mm" (bug #11)
                                date = convert_to_unc(fields[BOOKED_AT])
                                new_payment_entry.posting_date = date
                                #new_payment_entry.iban = fields[IBAN]
                                new_payment_entry.bic = fields[BIC]
                                new_payment_entry.paid_to = account
                                # remove thousands separator
                                new_payment_entry.received_amount = received_amount
                                new_payment_entry.paid_amount = received_amount
                                new_payment_entry.reference_no = transaction_id
                                new_payment_entry.reference_date = date
                                # Extract IBAN from "Vorgang/Verwendungszweck"
                                lineString = lines[i].replace("\n","").replace('"',"")
                                new_payment_entry.remarks = lineString
                                mo = re.search(r'IBAN\: ?(?P<IBAN>[A-Z]{2}(?:[ ]?[0-9]){18,20})', lineString)
                                if mo is not None:
                                    new_payment_entry.iban = mo.group('IBAN')
                                inserted_payment_entry = new_payment_entry.insert()
                                if auto_submit:
                                    new_payment_entry.submit()
                                new_payment_entries.append(inserted_payment_entry.name)

        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )

def parse_ksk(content, account, auto_submit=False):
    # parse a kreissparkasse bank extract in csv format
    #
    # Column definition:
    # Auftragskonto (0), Buchungstag (1), Valutadatum (2), Buchungstext (3),
    # Verwendungszweck (4), Glaeubiger ID (5), Mandatsreferenz (6), Kundenreferenz (End-to-End) (7),
    # Sammlerreferenz (8), Lastschrift Ursprungsbetrag (9), Auslagenersatz Ruecklastschrift (10),
    # Beguenstigter/Zahlungspflichtiger (11), Kontonummer/IBAN (12), BIC (SWIFT-Code) (13),
    # Betrag (14), Waehrung (15), Info(16)
    #
    BOOKED_AT = 1
    VALUTA = 2
    MODEOFPAYMENT = 3
    SENDER = 11
    IBAN = 12
    BIC = 13
    AMOUNT = 14

    # cell separator: ;
    # collect all lines of the file
    # log("Starting parser...")
    lines = content.split("\r\n")
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    try:
    # if True: # this is for detailed debug messages ;-)
        for i in range(1, len(lines)):
            #log("Reading {0} of {1} lines...".format(i, len(lines)))
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].replace("\r\n","~").replace('"',"").split(';')
            # get received amount, only continue if this has a POSITIVE value
            if len(fields) > 16:
                if fields[AMOUNT] != "":
                    # skip second lines (additional data for payments)
                    received_amount = float(fields[AMOUNT].replace(".","").replace(",","."))
                    #log("Received amount {0}".format(received_amount))
                    if received_amount > 0:
                        # get unique transaction ID
                        transaction_id = hashlib.md5("{0}:{1}:{2}".format(fields[BOOKED_AT], fields[AMOUNT], fields[SENDER])).hexdigest()
                        #log("Checking transaction {0}".format(transaction_id))
                        # cross-check if this transaction was already recorded
                        if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
                            #log("Adding transaction {0}".format(transaction_id))
                            # create new payment entry
                            new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                            new_payment_entry.payment_type = "Receive"
                            new_payment_entry.party_type = "Customer";
                            # get the customer name
                            customer_name = fields[SENDER]
                            customer = frappe.get_value('Customer', customer_name, 'name')
                            if customer:
                                new_payment_entry.party = customer
                            else:
                                new_payment_entry.party = default_customer
                            # date is in "DD.MM.YYYY hh.mm" or "YYYY-MM-DD hh:mm" (bug #11)
                            # frappe.throw(("ABC "+new_payment_entry.party))
                            date = convert_to_unc(fields[BOOKED_AT])
                            new_payment_entry.posting_date = date
                            new_payment_entry.iban = fields[IBAN]
                            new_payment_entry.bic = fields[BIC]
                            new_payment_entry.paid_to = account
                            # remove thousands separator
                            new_payment_entry.received_amount = received_amount
                            new_payment_entry.paid_amount = received_amount
                            new_payment_entry.reference_no = transaction_id
                            new_payment_entry.reference_date = date
                            new_payment_entry.remarks = lines[i].replace("\n","~").replace('"',"")

                            inserted_payment_entry = new_payment_entry.insert()
                            if auto_submit:
                                new_payment_entry.submit()
                            new_payment_entries.append(inserted_payment_entry.name)
        return new_payment_entries
    except IndexError:
        frappe.throw( _("Parsing error. Make sure the correct bank is selected.") )

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
    # update unallocated amount
    payment_record = frappe.get_doc("Payment Entry", payment_entry)
    payment_record.unallocated_amount -= reference_entry.allocated_amount
    payment_record.save()
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

# convert a European/Swiss date format DD.MM.YYYY into UNC YYYY-MM-DD         
def convert_to_unc(ch_date):
    # check if is really .-separated (see bugfix #11)
    if '.' in ch_date:
        date_parts = ch_date.split('.')
        return date_parts[2] + "-" + date_parts[1] + "-" + date_parts[0]
    else:
        return ch_date

def get_default_customer():
    default_customer = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "default_customer")
    if not default_customer:
        default_customer = "Guest"
    return default_customer

@frappe.whitelist()
def get_bank_settings():
    # load ERPNextSwiss Bank Import Settings
    bank_settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings").bankimport_table
    # check result
    if not bank_settings:
        frappe.throw("No Bank settings found")
    # return bank settings objects
    selectable_banks = []
    for bank in bank_settings:
        # Return enabled banks for selection
        if bank.bank_enabled == True:
            selectable_banks.append({
                "bank_name":bank.bank_name,
                "legacy_ref":bank.legacy_ref,
                "file_format":bank.file_format}
            )
    return { "banks": selectable_banks}

@frappe.whitelist()
def parse_file(content, bank, account, auto_submit=False, debug=False):
    debug = assert_bool(debug)
    # content is the plain text content, parse
    auto_submit = assert_bool(auto_submit);
    new_records = []
    # Check if bank csv template is available
    try:
        if debug: frappe.msgprint("Bank: "+ bank)
        bank_doc = frappe.get_all("BankImport Bank", filters={'legacy_ref': bank}, fields=['csv_template'])
    except:
        bank_doc = None
    if bank_doc and bank_doc[0]['csv_template']:
        if debug: frappe.msgprint(_("Parse file by template"))
        new_records = parse_by_template(content, bank_doc[0]['csv_template'], account, auto_submit, debug)
    else:
        # Decode content with default ascii encoding in Python 2.x
        if six.PY2:
            content = (b""+ content).decode("ascii")

        if bank == "ubs":
            new_records = parse_ubs(content, account, auto_submit)
        elif bank == "zkb":
            new_records = parse_zkb(content, account, auto_submit)
        elif bank == "raiffeisen":
            new_records = parse_raiffeisen(content, account, auto_submit)
        elif bank == "cs":
            new_records = parse_cs(content, account, auto_submit)
        elif bank == "migrosbank":
            new_records = parse_migrosbank(content, account, auto_submit)
        elif bank == "voba":
            new_records = parse_voba(content, account, auto_submit)
        elif bank == "ksk":
            new_records = parse_ksk(content, account, auto_submit)
        else:
            frappe.msgprint( _("No suitable parser found") )

    message = "Completed"
    if len(new_records) == 0:
        if not debug: message = "No new transactions found"
        
    if not debug:
        return { "message": message, "records": new_records }
    else:
        return { "message": "Debug Completed", "records": new_records }

# this function tries to process the content by csv template information
# 
# returns the payment entries as list or None
@frappe.whitelist()
def parse_by_template(content, bank, account, auto_submit=False, debug=False):
    # load csv template information
    template = frappe.get_doc("BankImport Template",bank)
    
    # collect all lines of the file
    if six.PY2:
        content = (b""+ content).decode(template.file_encoding)
    
    # collect created payment entries
    new_payment_entries = []
    # get default customer
    default_customer = get_default_customer()
    
    # this function tries to get docitem value by name
    # 
    # returns the value as string, int or None
    # string escape chars are removed
    def getFieldDefinition(docItemName, template=template):
        # get value from csv template
        value = getattr(template,docItemName,None)
        if value is not None:
            if isinstance(value, six.string_types):
                # remove escape chars and return value
                if six.PY2:
                    return value.decode("unicode_escape")
                else:
                    return bytearray(value, "utf-8").decode("unicode_escape")
            elif isinstance(value, int):
                if int(value) >= 0:
                    return int(value)
                else:
                    return None
            else:
                frappe.throw(_("Unknown parameter. Error: {0}").format(str(e)))
        else:
            return value
    # this function checks the available field properties and process them
    # accordingly
    # 
    # returns the value as string. Rise an error if field is required
    def getProcessedValue(fieldname, field_definition, fields):
        # Check if field index is defined
        if isinstance(field_definition["field_index"], int):
            field_value = fields[field_definition["field_index"]]
            if field_value:
                if field_definition["field_reg"]:
                    # Process regex matching
                    m = re.search(field_definition["field_reg"],field_value)
                    try:
                        field_value = m.group(field_definition["match_group"])
                        return field_value
                    except Exception as e:
                        # Return empty string if regex did not match
                        if(not field_definition["regired"]):
                            return ""
                        frappe.throw(_("Regex of '{0}' did not match with error: {1}").format(fieldname, str(e)))
                else:
                    return field_value
            elif not field_value and field_definition["regired"]:
                frappe.throw(_("Value not found for '{0}' and index: {1}").format(fieldname, field_definition["field_index"]))
            else:
                return ""
        elif not field_definition["regired"]:
            return ""
        else:
            frappe.throw(_("Undefined condition for '{0}'").format(fieldname))
    
    # collect field mapping information from 'BankImport Template'
    field_definitions = {
        'BOOKED_AT' :
            { 'field_index': getFieldDefinition('booked_at_field'),'field_reg': getFieldDefinition('booked_at_reg'),'match_group': 'booked','regired': True},
        'AMOUNT' :
            { 'field_index': getFieldDefinition('amount_field'),'field_reg': getFieldDefinition('amount_reg'),'match_group': 'amount','regired': False},
        'CUSTOMER' :
            { 'field_index': getFieldDefinition('customer_field'),'field_reg': getFieldDefinition('customer_reg'),'match_group': 'customer','regired': False},
        'TRANSACTION' :
            { 'field_index': getFieldDefinition('transaction_field'),'field_reg': getFieldDefinition('transaction_reg'),'match_group': 'transaction','regired': True},
        'REMARK' :
            { 'field_index': getFieldDefinition('remark_field'),'field_reg': getFieldDefinition('remark_reg'),'match_group': 'remark','regired': False},
        'IBAN' :
            { 'field_index': getFieldDefinition('iban_field'),'field_reg': getFieldDefinition('iban_reg'),'match_group': 'iban','regired': False},
        'BIC' :
            { 'field_index': getFieldDefinition('bic_field'),'field_reg': getFieldDefinition('bic_reg'),'match_group': 'bic','regired': False},
        'VALUTA' :
            { 'field_index': getFieldDefinition('valuta_field'),'field_reg': getFieldDefinition('valuta_reg'),'match_group': 'valuta','regired': False}
    }

    # Process advanced content regex substitution
    if template.advanced_settings:
        if getattr(template,"content_regex",None):
            #Process each content replacement item
            for item in template.content_regex:
                content = tpl_regex_replace(item.reg_match, item.reg_sub, content, item.titel)
    
    # Split content lines
    try:
        if six.PY2:
            lines = content.split(template.line_seperator.decode("unicode_escape"))
        else:
            lines = content.split(bytearray(template.line_seperator, "utf-8").decode("unicode_escape"))
    except Exception as e:
        frappe.throw(_("Could not split lines by \"{0}\" with error: {1}").format(bytearray(template.line_seperator, "utf-8").decode("unicode_escape"), str(e)))
    if debug:
        frappe.msgprint("Content: {1}, Lines: {0}, separator: {2}".format(len(lines), content, template.line_seperator))
    try:
        if debug: frappe.msgprint(_("Header line:<br>" + lines[template.header_skip - 1]))
        if debug: frappe.msgprint(_("Last line:<br>" + lines[len(lines) - template.footer_skip - 1]))
        for i in range(template.header_skip, (len(lines) - template.footer_skip)):
            # Process advanced line regex substitution
            if template.advanced_settings:
                if getattr(template,"line_regex",None):
                    #Process each line replacement item
                    for item in template.line_regex:
                        lines[i] = tpl_regex_replace(item.reg_match, item.reg_sub, lines[i], item.titel)
                        
            # Split fields by delimiter
            if six.PY2:
                fields = lines[i].split(template.delimiter.decode("unicode_escape"))
            else:
                fields = lines[i].split(bytearray(template.delimiter, "utf-8").decode("unicode_escape"))
            # Print line with field index
            if debug:
                string = ""
                for f in range(len(fields)):
                    string = string + str(f) + ": " + fields[f] + " "
                frappe.msgprint(string)
            # Validate line by the minimum field count
            if debug: frappe.msgprint(_("Line {0} has a field count of {1}. Min is ({2})").format(
                str(i),
                str(len(fields)),
                str(template.min_field_count))
            )
            if len(fields) >= int(template.min_field_count):
                if debug:
                    frappe.msgprint(fields)
                valid = True
                # Process validation if specified
                if template.advanced_settings:
                    validationField = getattr(template,"valid_field",None)
                    if validationField:
                        # Get function from operator module and run validation
                        if not getattr(operator, template.valid_operator)(fields[validationField], template.valid_value):
                            if debug: 
                                frappe.msgprint(_("Line not valid. Field value '{0}' and '{1}' with operator '{2}' evaluates false").format(
                                    fields[validationField],
                                    template.valid_value,
                                    template.valid_operator
                                ))
                            valid = False
                        if valid and debug:
                            frappe.msgprint(_("Line valid"))
                # Assign payment entry values
                amount = getProcessedValue("AMOUNT",field_definitions["AMOUNT"], fields)
                if valid and amount != "":
                    try:
                        # Assign empty string to amount seperators (can be None if template is imported)
                        if template.k_separator:
                            k_separator = template.k_separator
                        else: 
                            k_separator = "'"
                        if template.decimal_separator:
                            decimal_separator = template.decimal_separator
                        else: 
                            decimal_separator = "."
                        received_amount = float(amount.replace(k_separator,"").replace(decimal_separator,"."))
                    except Exception as e:
                        frappe.throw(_("Could not parse amount with value {0} check thousand and decimal separator. Error: {1}").format(amount, str(e)))
                    if received_amount > 0:
                        booked_at = datetime.strptime(getProcessedValue("BOOKED_AT",field_definitions["BOOKED_AT"], fields),template.date_format)
                        try:
                            # Try to assing valuta value
                            valuta = datetime.strptime(getProcessedValue("VALUTA",field_definitions["VALUTA"], fields),template.date_format)
                        except Exception as e:
                            # Use 'booked_at' because valuta did not evaluate
                            valuta = booked_at
                        customerMapping = getProcessedValue("CUSTOMER",field_definitions["CUSTOMER"], fields)
                        
                        # If specified use hash as reference instead of ref field
                        if template.transaction_hash == 1:
                            source = "{0}:{1}:{2}".format(booked_at, received_amount, customerMapping).encode('utf-8')
                            transaction_id = hashlib.md5(source).hexdigest()
                        else:
                            transaction_id = getProcessedValue("TRANSACTION",field_definitions["TRANSACTION"], fields)
                        
                        # Check if payment already exist
                        if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}) or debug:
                            new_payment_entry = frappe.get_doc({'doctype': 'Payment Entry'})
                            new_payment_entry.payment_type = "Receive"
                            new_payment_entry.party_type = "Customer";
                            
                            # Try to match customer field with existing customer
                            customer = frappe.get_value('Customer', customerMapping, 'name')
                            if customer:
                                new_payment_entry.party = customerMapping
                            else:
                                new_payment_entry.party = default_customer
                            new_payment_entry.posting_date = booked_at
                            new_payment_entry.paid_to = account
                            new_payment_entry.received_amount = received_amount
                            new_payment_entry.paid_amount = received_amount
                            new_payment_entry.camt_amount = received_amount
                            new_payment_entry.reference_no = transaction_id
                            new_payment_entry.reference_date = valuta
                            new_payment_entry.iban = getProcessedValue("IBAN",field_definitions["IBAN"], fields)
                            new_payment_entry.bic = getProcessedValue("BIC",field_definitions["BIC"], fields)
                            
                            # If remark field is not defined or cannot be found use whole line
                            remark = getProcessedValue("REMARK",field_definitions["REMARK"], fields)
                            if remark:
                                new_payment_entry.remarks = remark
                            else:
                                new_payment_entry.remarks = lines[i]
                            if debug: frappe.msgprint(frappe.as_json(new_payment_entry).replace("\n","<br>"))
                            if not debug:
                                inserted_payment_entry = new_payment_entry.insert()
                                if auto_submit:
                                    new_payment_entry.submit()
                                new_payment_entries.append(inserted_payment_entry.name)
        return new_payment_entries
    except Exception as e:
        frappe.throw(_("Failed to parse lines with error: {0}").format(str(e)))

def tpl_regex_replace(reg_find, reg_replace, content, stage, reg_group=""):
    # Validate arguments
    try:
        if not isinstance(reg_find, six.string_types) and not reg_find:
            frappe.throw("Template parameter invalid, please check regex find setting")
        else:
            if six.PY2:
                reg_find = reg_find.decode("unicode_escape")
            else:
                reg_find = bytearray(reg_find, "utf-8").decode("unicode_escape")
        if not isinstance(reg_replace, six.string_types):
            reg_replace = ""
        elif not reg_replace:
            reg_replace = ""
        else:
            if six.PY2:
                reg_replace = reg_replace.decode("unicode_escape")
            else:
                reg_replace = bytearray(reg_replace, "utf-8").decode("unicode_escape")
    except Exception as e:
        frappe.throw(_("Validation failed with error: {0}").format(str(e)))
    # Substitute content with regex
    try:
        return re_sub(reg_find, reg_replace, content)
    except Exception as e:
        frappe.throw(_("Could not manipulate argument at stage \"{0}\" with error: {1}").format(stage, str(e)))

#https://gist.github.com/gromgull/3922244
def re_sub(pattern, replacement, string):
    def _r(m):
        # Now this is ugly.
        # Python has a "feature" where unmatched groups return None
        # then re.sub chokes on this.
        # see http://bugs.python.org/issue1519638
        
        # this works around and hooks into the internal of the re module...

        # the match object is replaced with a wrapper that
        # returns "" instead of None for unmatched groups

        class _m():
            def __init__(self, m):
                self.m=m
                self.string=m.string
            def group(self, n):
                return m.group(n) or ""

        return re._expand(pattern, _m(m), replacement)
    
    return re.sub(pattern, _r, string)
    
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
    #doc = xmltodict.parse(content)
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
    
@frappe.whitelist()
def read_camt054(content, bank, account, auto_submit=False):
    soup = BeautifulSoup(content, 'lxml')
    
    # general information
    try:
        iban = soup.document.bktocstmrdbtcdtntfctn.ntfctn.acct.id.iban.get_text()
    except:
        # node not found, probably wrong format
        return { "message": _("Unable to read structure. Please make sure that you have selected the correct format."), "records": None }
        
    # transactions
    new_payment_entries = read_camt_transactions(soup.find_all('ntry'), bank, account, auto_submit)
    message = _("Successfully imported {0} payments.".format(len(new_payment_entries)))
    
    return { "message": message, "records": new_payment_entries } 
    
def read_camt_transactions(transaction_entries, bank, account, auto_submit=False):
    new_payment_entries = []
    for entry in transaction_entries:
        entry_soup = BeautifulSoup(unicode(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text()
        transactions = entry_soup.find_all('txdtls')
        # fetch entry amount as fallback
        entry_amount = float(entry_soup.amt.get_text())
        entry_currency = entry_soup.amt['ccy']
        for transaction in transactions:
            transaction_soup = BeautifulSoup(unicode(transaction), 'lxml')
            try:
                unique_reference = transaction_soup.refs.acctsvcrref.get_text()
                amount = float(transaction_soup.amt.get_text())
                currency = transaction_soup.amt['ccy']
                try:
                    party_soup = BeautifulSoup(unicode(transaction_soup.dbtr), 'lxml')
                    customer_name = party_soup.nm.get_text()
                    try:
                        street = party_soup.strtnm.get_text()
                        try:
                            street_number = party_soup.bldgnb.get_text()
                            address_line = "{0} {1}".format(street, street_number)
                        except:
                            address_line = street
                            
                    except:
                        address_line = ""
                    try:
                        plz = party_soup.pstcd.get_text()
                    except:
                        plz = ""
                    try:
                        town = party_soup.twnnm.get_text()
                    except:
                        town = ""
                    try:
                        country = party_soup.ctry.get_text()
                    except:
                        party_iban = ""
                    customer_address = "{0}, {1}, {2}".format(address_line, plz, town)
                    try:
                        customer_iban = "{0}".format(transaction_soup.dbtracct.id.iban.get_text())
                    except:
                        customer_iban = ""
                except:
                    # CRDT: use RltdPties:Dbtr
                    #party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.dbtr)) 
                    try:
                        customer_iban = transaction_soup.dbtracct.id.iban.get_text()
                    except Exception as e:
                        customer_iban = ""
                        frappe.log_error("Error parsing customer info: {0} ({1})".format(e, unicode(transaction_soup.dbtr)))
                        # key related parties not found / no customer info
                        customer_name = "Postschalter"
                        customer_address = ""
                try:
                    charges = float(transaction_soup.chrgs.ttlchrgsandtaxamt.get_text())
                except:
                    charges = 0.0
                # paid or received: (DBIT: paid, CRDT: received)
                credit_debit = transaction_soup.cdtdbtind.get_text()
                try:
                    # try to find ESR reference
                    transaction_reference = transaction_soup.rmtinf.strd.cdtrrefinf.ref.get_text()
                except:
                    try:
                        # try to find a user-defined reference (e.g. SINV.)
                        transaction_reference = transaction_soup.rmtinf.ustrd.get_text()
                    except:
                        try:
                            # try to find an end-to-end ID
                            transaction_reference = transaction_soup.refs.endtoendid.get_text()
                        except:
                            transaction_reference = unique_reference
                if credit_debit == "CRDT":
                    inserted_payment_entry = create_payment_entry(date=date, to_account=account, received_amount=amount, 
                        transaction_id=unique_reference, remarks="ESR: {0}, {1}, {2}, IBAN: {3}".format(
                        transaction_reference, customer_name, customer_address, customer_iban), 
                        auto_submit=False)
                    if inserted_payment_entry:
                        new_payment_entries.append(inserted_payment_entry.name)
            except Exception as e:
                frappe.msgprint("Parsing error: {0}:{1}".format(unicode(transaction), e))
                pass
    return new_payment_entries
