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
def read_camt053(content, account):
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
    transactions = read_camt_transactions(entries, account)
    
    return { 'transactions': transactions } 

def read_camt_transactions(transaction_entries, account):
    txns = []
    for entry in transaction_entries:
        entry_soup = BeautifulSoup(str(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text()
        transactions = entry_soup.find_all('ntrydtls')
        # fetch entry amount as fallback
        entry_amount = float(entry_soup.amt.get_text())
        entry_currency = entry_soup.amt['ccy']
        for transaction in transactions:
            transaction_soup = BeautifulSoup(str(transaction), 'lxml')
            # paid or received: (DBIT: paid, CRDT: received)
            try:
                credit_debit = transaction_soup.cdtdbtind.get_text()
            except:
                # fallback to entry indicator
                credit_debit = entry_soup.cdtdbtind.get_text()
            
            #try:
            try:
                # try to use the account service reference
                unique_reference = transaction_soup.txdtls.refs.acctsvcrref.get_text()
            except:
                # fallback: use tx id
                try:
                    unique_reference = transaction_soup.txid.get_text()
                except:
                    # fallback to pmtinfid
                    unique_reference = transaction_soup.pmtinfid.get_text()
            try:
                amount = float(transaction_soup.txdtls.amt.get_text())
                currency = transaction_soup.txdtls.amt['ccy']
            except:
                # fallback to amount from entry level
                amount = entry_amount
                currency = entry_currency
            try:
                if credit_debit == "DBIT":
                    # use RltdPties:Cdtr
                    party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.cdtr)) 
                    try:
                        party_iban = transaction_soup.cdtracct.id.iban.get_text()
                    except:
                        party_iban = ""
                else:
                    # CRDT: use RltdPties:Dbtr
                    party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.dbtr)) 
                    try:
                        party_iban = transaction_soup.dbtracct.id.iban.get_text()
                    except:
                        party_iban = ""
                try:
                    party_name = party_soup.nm.get_text()
                    if party_soup.strtnm:
                        # parse by street name, ...
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
                        address_line2 = "{0} {1}".format(plz, town)
                    else:
                        # parse by address lines
                        address_lines = party_soup.find_all("adrline")
                        address_line1 = address_lines[0].get_text()
                        address_line2 = address_lines[1].get_text()
                except:
                    # party is not defined (e.g. DBIT from Bank)
                    party_name = "not found"
                    address_line1 = ""
                    address_line2 = ""
                try:
                    country = party_soup.ctry.get_text()
                except:
                    country = ""
                party_address = "{0}, {1}, {2}".format(
                    address_line1,
                    address_line2,
                    country)
            except:
                # key related parties not found / no customer info
                party_name = ""
                party_address = ""
                party_iban = ""
            try:
                charges = float(transaction_soup.chrgs.ttlchrgsandtaxamt[text])
            except:
                charges = 0.0

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
                        transaction_reference = transaction_soup.cdtdbtind.get_text() 
                    except:
                        transaction_reference = unique_reference
            frappe.log_error("type:{type}\ndate:{date}\namount:{currency} {amount}\nunique ref:{unique}\nparty:{party}\nparty address:{address}\nparty iban:{iban}\nremarks:{remarks}".format(
                type=credit_debit, date=date, currency=currency, amount=amount, unique=unique_reference, party=party_name, address=party_address, iban=party_iban, remarks=transaction_reference))
            
            new_txn = {
                'date': date,
                'currency': currency,
                'amount': amount,
                'party_name': party_name,
                'party_address': party_address,
                'credit_debit': credit_debit,
                'party_iban': party_iban,
                'unique_reference': unique_reference,
                'transaction_reference': transaction_reference
            }
            txns.append(new_txn)    
            #if credit_debit == "CRDT":
            #    inserted_payment_entry = create_payment_entry(date=date, to_account=account, received_amount=amount, 
            #        transaction_id=unique_reference, remarks="ESR: {0}, {1}, {2}, IBAN: {3}".format(
            #        transaction_reference, customer_name, customer_address, customer_iban), 
            #        auto_submit=False)
            #    if inserted_payment_entry:
            #        new_payment_entries.append(inserted_payment_entry.name)
            #except Exception as e:
            #    frappe.msgprint("Parsing error: {0}:{1}".format(str(transaction), e))
            #    pass

    return txns
