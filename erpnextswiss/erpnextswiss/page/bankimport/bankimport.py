# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import hashlib
from bs4 import BeautifulSoup
import json

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
        for i in range(1, len(lines)):
            #log("Reading {0} of {1} lines...".format(i, len(lines)))
            # skip line 0, it contains the column headers
            # collect each fields (separated by semicolon)
            fields = lines[i].split(';')
           
            # get received amount, only continue if this has a value
            if len(fields) > 10:
                received_amount = fields[7]
                #log("Received amount {0} ({1}, {2})".format(received_amount, fields[18], fields[20]))
                if received_amount != "":
                    # get unique transaction ID
                    transaction_id = fields[4]
                    #log("Checking transaction {0}".format(transaction_id))
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
                        long_customer_text = description[1].split(",")
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
                            new_payment_entry.remarks = fields_next_row[1] + ", " + fields_next_row[10]
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
    # if True: # this is for detailed debug messages ;-)
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
                        transaction_id = hashlib.md5("{0}{1}{2}".format(fields[BOOKED_AT], fields[TEXT], fields[AMOUNT])).hexdigest()
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
                                new_payment_entry.remarks = fields[TEXT]
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
def parse_file(content, bank, account, auto_submit=False):
    # content is the plain text content, parse 
    auto_submit = assert_bool(auto_submit);
   
    new_records = []
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
                       
    message = "Completed"
    if len(new_records) == 0:
        message = "No new transactions found"
        
    return { "message": message, "records": new_records }

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
    doc = xmltodict.parse(content)
    
    # general information
    try:
        iban = doc['Document']['BkToCstmrStmt']['Stmt']['Acct']['Id']['IBAN']
    except:
        # node not found, probably wrong format
        return { "message": _("Unable to read structure. Please make sure that you have selected the correct format."), "records": None }
            
    # transactions
    new_payment_entries = read_camt_transactions(doc['Document']['BkToCstmrStmt']['Stmt']['Ntry'], bank, account, auto_submit)
                
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
                        country = ""
                    customer_address = "{0}, {1} {2}, {3}".format(
                        address_line,
                        plz,
                        town,
                        country)
                    try:
                        customer_iban = transaction_soup.dbtracct.id.iban.get_text()
                    except:
                        customer_iban = ""
                except Exception as e:
                    frappe.log_error("Error parsing customer info: {0} ({1})".format(e, transaction_soup.dbtr.get_text()))
                    # key related parties not found / no customer info
                    customer_name = "Postschalter"
                    customer_address = ""
                    customer_iban = ""
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
                frappe.msgprint("Parsing error: {0}:{1}".format(str(transaction), e))
                pass
    return new_payment_entries
