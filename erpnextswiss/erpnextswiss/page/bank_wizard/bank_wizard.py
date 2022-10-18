# -*- coding: utf-8 -*-
# Copyright (c) 2017-2022, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import hashlib
import json
from bs4 import BeautifulSoup
import ast
import cgi                              # (used to escape utf-8 to html)
import six
from frappe.utils import cint
from frappe.utils.data import get_url_to_form

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
def create_payment_entry(date, to_account, received_amount, transaction_id, remarks, party_iban=None, auto_submit=False):
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
        new_payment_entry.bank_account_no = party_iban
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
    accounts = frappe.get_list('Account', filters={'account_type': 'Bank', 'is_group': 0}, fields=['name'], order_by='account_number')
    selectable_accounts = []
    for account in accounts:
        selectable_accounts.append(account.name)

    # frappe.throw(selectable_accounts)
    return {'accounts': selectable_accounts }

@frappe.whitelist()
def get_default_accounts(bank_account):
    company = frappe.get_value("Account", bank_account, "company")
    receivable_account = frappe.get_value('Company', company, 'default_receivable_account')
    payable_account = frappe.get_value('Company', company, 'default_payable_account')
    expense_payable_account = frappe.get_value('Company', company, 'default_expense_claim_payable_account') or payable_account
    auto_process_matches = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'auto_process_matches')
    return { 
        'company': company, 
        'receivable_account': receivable_account, 
        'payable_account': payable_account, 
        'expense_payable_account': expense_payable_account,
        'auto_process_matches': auto_process_matches
    }

@frappe.whitelist()
def get_intermediate_account():
    account = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'intermediate_account')
    return {'account': account or "" }

@frappe.whitelist()
def get_default_customer():
    customer = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'default_customer')
    return {'customer': customer or "" }
    
@frappe.whitelist()
def get_default_supplier():
    supplier = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'default_supplier')
    return {'supplier': supplier or "" }
    
@frappe.whitelist()
def get_receivable_account(company=None):
    if not company:
        company = get_first_company()
    account = frappe.get_value('Company', company, 'default_receivable_account')
    return {'account': account or "" }

@frappe.whitelist()
def get_payable_account(company=None, employee=False):
    if not company:
        company = get_first_company()
    account = frappe.get_value('Company', company, 'default_payable_account')
    if employee:
        account = frappe.get_value('Company', company, 'default_expense_claim_payable_account') or account
    return {'account': account or "" }

def get_first_company():
    companies = frappe.get_all("Company", filters=None, fields=['name'])
    return companies[0]['name']

@frappe.whitelist()
def read_camt053(content, account):
    settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
    
    #read_camt_transactions_re(content)
    soup = BeautifulSoup(content, 'lxml')
    
    # general information
    try:
        #iban = doc['Document']['BkToCstmrStmt']['Stmt']['Acct']['Id']['IBAN']
        iban = soup.document.bktocstmrstmt.stmt.acct.id.iban.get_text()
    except:
        # fallback (Credit Suisse will provide bank account number instead of IBAN)
        iban = "n/a"
        try:
            acct_no = soup.document.bktocstmrstmt.stmt.acct.id.othr.id.get_text()
        except:
            # node not found, probably wrong format
            iban = "n/a"
            frappe.log_error("Unable to read structure. Please make sure that you have selected the correct format.", "BankWizard read_camt053")
            
    # verify iban
    account_iban = frappe.get_value("Account", account, "iban")
    if account_iban and account_iban.replace(" ", "") != iban.replace(" ", ""):
        frappe.log_error( _("IBAN mismatch {0} (account) vs. {1} (file)").format(account_iban, iban), _("Bank Import IBAN validation") )
        frappe.msgprint( _("IBAN mismatch {0} (account) vs. {1} (file)").format(account_iban, iban), _("Bank Import IBAN validation") )

    # transactions
    entries = soup.find_all('ntry')
    transactions = read_camt_transactions(entries, account, settings)
    
    return { 'transactions': transactions } 
    
def read_camt_transactions(transaction_entries, account, settings, debug=False):
    company = frappe.get_value("Account", account, "company")
    txns = []
    for entry in transaction_entries:
        if six.PY2:
            entry_soup = BeautifulSoup(unicode(entry), 'lxml')
        else:
            entry_soup = BeautifulSoup(str(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text()
        transactions = entry_soup.find_all('txdtls')
        # fetch entry amount as fallback
        entry_amount = float(entry_soup.amt.get_text())
        entry_currency = entry_soup.amt['ccy']
        # fetch global account service reference
        try:
            global_account_service_reference = entry_soup.acctsvcrref.get_text()
        except:
            global_account_service_reference = ""
        transaction_count = 0
        if transactions and len(transactions) > 0:
            for transaction in transactions:
                transaction_count += 1
                if six.PY2:
                    transaction_soup = BeautifulSoup(unicode(transaction), 'lxml')
                else:
                    transaction_soup = BeautifulSoup(str(transaction), 'lxml')
                # --- find transaction type: paid or received: (DBIT: paid, CRDT: received)
                if settings.always_use_entry_transaction_type:
                    credit_debit = entry_soup.cdtdbtind.get_text()
                else:
                    try:
                        credit_debit = transaction_soup.cdtdbtind.get_text()
                    except:
                        # fallback to entry indicator
                        credit_debit = entry_soup.cdtdbtind.get_text()
                
                # collect payment instruction id
                try:
                    payment_instruction_id = transaction_soup.pmtinfid.get_text()
                except:
                    payment_instruction_id = None
                
                # --- find unique reference
                try:
                    # try to use the account service reference
                    unique_reference = transaction_soup.txdtls.refs.acctsvcrref.get_text()
                except:
                    # fallback: use tx id
                    try:
                        unique_reference = transaction_soup.txid.get_text()
                    except:
                        # fallback to pmtinfid
                        try:
                            unique_reference = transaction_soup.pmtinfid.get_text()
                        except:
                            # fallback to group account service reference plus transaction_count
                            if global_account_service_reference != "":
                                unique_reference = "{0}-{1}".format(global_account_service_reference, transaction_count)
                            else:
                                # fallback to ustrd (do not use)
                                # unique_reference = transaction_soup.ustrd.get_text()
                                # fallback to hash
                                amount = transaction_soup.txdtls.amt.get_text()
                                party = transaction_soup.nm.get_text()
                                code = "{0}:{1}:{2}".format(date, amount, party)
                                frappe.log_error("Code: {0}".format(code))
                                unique_reference = hashlib.md5(code.encode("utf-8")).hexdigest()
                # --- find amount and currency
                try:
                    # try to find as <TxAmt>
                    amount = float(transaction_soup.txdtls.txamt.amt.get_text())
                    currency = transaction_soup.txdtls.txamt.amt['ccy']
                except:
                    try:
                        # fallback to pure <AMT>
                        amount = float(transaction_soup.txdtls.amt.get_text())
                        currency = transaction_soup.txdtls.amt['ccy']
                    except:
                        # fallback to amount from entry level
                        amount = entry_amount
                        currency = entry_currency
                try:
                    # --- find party IBAN
                    if credit_debit == "DBIT":
                        # use RltdPties:Cdtr
                        if six.PY2:
                            party_soup = BeautifulSoup(unicode(transaction_soup.txdtls.rltdpties.cdtr), 'lxml') 
                        else:
                            party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.cdtr), 'lxml') 
                        try:
                            party_iban = transaction_soup.cdtracct.id.iban.get_text()
                        except:
                            party_iban = ""
                    else:
                        # CRDT: use RltdPties:Dbtr
                        if six.PY2:
                            party_soup = BeautifulSoup(unicode(transaction_soup.txdtls.rltdpties.dbtr), 'lxml')
                        else:
                            party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.dbtr), 'lxml')
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
                                    address_line1 = "{0} {1}".format(street, street_number)
                                except:
                                    address_line1 = street
                                    
                            except:
                                address_line1 = ""
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
                            try:
                                address_lines = party_soup.find_all("adrline")
                                address_line1 = address_lines[0].get_text()
                                address_line2 = address_lines[1].get_text()
                            except:
                                # in case no address is provided
                                address_line1 = ""
                                address_line2 = ""                            
                    except:
                        # party is not defined (e.g. DBIT from Bank)
                        try:
                            # this is a fallback for ZKB which does not provide nm tag, but address line
                            address_lines = party_soup.find_all("adrline")
                            party_name = address_lines[0].get_text()
                        except:
                            party_name = "not found"
                        address_line1 = ""
                        address_line2 = ""
                    try:
                        country = party_soup.ctry.get_text()
                    except:
                        country = ""
                    if (address_line1 != "") and (address_line2 != ""):
                        party_address = "{0}, {1}, {2}".format(
                            address_line1,
                            address_line2,
                            country)
                    elif (address_line1 != ""):
                        party_address = "{0}, {1}".format(address_line1, country)
                    else:
                        party_address = "{0}".format(country)
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
                            transaction_reference = transaction_soup.endtoendid.get_text() 
                        except:
                            try:
                                # try to find an AddtlTxInf
                                transaction_reference = transaction_soup.addtltxinf.get_text() 
                            except:
                                # in case of numeric only matching, do not fall back to transaction id
                                if cint(settings.numeric_only_debtor_matching) == 1:
                                    transaction_reference = "???"
                                else:
                                    transaction_reference = unique_reference
                # debug: show collected record in error log
                #frappe.log_error("""type:{type}\ndate:{date}\namount:{currency} {amount}\nunique ref:{unique}
                #    party:{party}\nparty address:{address}\nparty iban:{iban}\nremarks:{remarks}
                #    payment_instruction_id:{payment_instruction_id}""".format(
                #    type=credit_debit, date=date, currency=currency, amount=amount, unique=unique_reference, 
                #    party=party_name, address=party_address, iban=party_iban, remarks=transaction_reference,
                #    payment_instruction_id=payment_instruction_id))
                
                # check if this transaction is already recorded
                match_payment_entry = frappe.get_all('Payment Entry', 
                    filters={'reference_no': unique_reference, 'company': company}, 
                    fields=['name'])
                if match_payment_entry:
                    if debug:
                        frappe.log_error("Transaction {0} is already imported in {1}.".format(unique_reference, match_payment_entry[0]['name']))
                else:
                    # try to find matching parties & invoices
                    party_match = None
                    employee_match = None
                    invoice_matches = []
                    expense_matches = None
                    matched_amount = 0.0
                    if credit_debit == "DBIT":
                        # match by payment instruction id
                        possible_pinvs = []
                        if payment_instruction_id:
                            try:
                                payment_instruction_fields = payment_instruction_id.split("-")
                                payment_instruction_row = int(payment_instruction_fields[-1]) + 1
                                if len(payment_instruction_fields) > 3:
                                    # revision in payment proposal
                                    payment_proposal_id = "{0}-{1}".format(payment_instruction_fields[1], payment_instruction_fields[2])
                                else:
                                    payment_proposal_id = payment_instruction_fields[1]
                                # find original instruction record
                                payment_proposal_payments = frappe.get_all("Payment Proposal Payment", 
                                    filters={'parent': payment_proposal_id, 'idx': payment_instruction_row},
                                    fields=['receiver', 'receiver_address_line1', 'receiver_address_line2', 'iban', 'reference', 'receiver_id', 'esr_reference'])
                                # supplier
                                if payment_proposal_payments:
                                    if payment_proposal_payments[0]['receiver_id'] and frappe.db.exists("Supplier", payment_proposal_payments[0]['receiver_id']):
                                        party_match = payment_proposal_payments[0]['receiver_id']
                                    else:
                                        # fallback to supplier name
                                        match_suppliers = frappe.get_all("Supplier", filters={'supplier_name': payment_proposal_payments[0]['receiver']}, 
                                            fields=['name'])
                                        if match_suppliers and len(match_suppliers) > 0:
                                            party_match = match_suppliers[0]['name']
                                    # purchase invoice reference match (take each part separately)
                                    if payment_proposal_payments[0]['esr_reference']:
                                        # match by esr reference number
                                        possible_pinvs = frappe.get_all("Purchase Invoice",
                                            filters=[['docstatus', '=', 1],
                                                ['outstanding_amount', '>', 0],
                                                ['esr_reference_number', '=', payment_proposal_payments[0]['esr_reference']]
                                            ],
                                            fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                                    else:
                                        # check each individual reference (combined pinvs)
                                        possible_pinvs = frappe.get_all("Purchase Invoice",
                                                filters=[['docstatus', '=', 1],
                                                    ['outstanding_amount', '>', 0],
                                                    ['bill_no', 'IN', payment_proposal_payments[0]['reference']]
                                                ],
                                                fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                            except Exception as err:
                                # this can be the case for malformed instruction ids
                                frappe.log_error(err, "Match payment instruction error")
                        # suppliers 
                        if not possible_pinvs:
                            # no payment proposal, try to estimate from other data
                            if not party_match:
                                # find suplier from name
                                match_suppliers = frappe.get_all("Supplier", 
                                    filters={'supplier_name': party_name, 'disabled': 0}, 
                                    fields=['name'])
                                if match_suppliers:
                                    party_match = match_suppliers[0]['name']
                            if party_match:
                                # restrict pinvs to supplier
                                possible_pinvs = frappe.get_all("Purchase Invoice",
                                    filters=[['docstatus', '=', 1], ['outstanding_amount', '>', 0], ['supplier', '=', party_match]],
                                    fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                            else:
                                # purchase invoices
                                possible_pinvs = frappe.get_all("Purchase Invoice", 
                                    filters=[['docstatus', '=', 1], ['outstanding_amount', '>', 0]], 
                                    fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                        if possible_pinvs:
                            for pinv in possible_pinvs:
                                if ((pinv['name'] in transaction_reference) \
                                    or ((pinv['bill_no'] or pinv['name']) in transaction_reference) \
                                    or (pinv['esr_reference_number'] and pinv['esr_reference_number'] in transaction_reference)):
                                    invoice_matches.append(pinv['name'])
                                    # override party match in case there is one from the sales invoice
                                    party_match = pinv['supplier']
                                    # add total matched amount
                                    matched_amount += float(pinv['outstanding_amount'])
                        # employees 
                        match_employees = frappe.get_all("Employee", 
                            filters={'employee_name': party_name, 'status': 'active'}, 
                            fields=['name'])
                        if match_employees:
                            employee_match = match_employees[0]['name']
                        # expense claims
                        possible_expenses = frappe.get_all("Expense Claim", 
                            filters=[['docstatus', '=', 1], ['status', '=', 'Unpaid']], 
                            fields=['name', 'employee', 'total_claimed_amount'])
                        if possible_expenses:
                            expense_matches = []
                            for exp in possible_expenses:
                                if exp['name'] in transaction_reference:
                                    expense_matches.append(exp['name'])
                                    # override party match in case there is one from the sales invoice
                                    employee_match = exp['employee']
                                    # add total matched amount
                                    matched_amount += float(exp['total_claimed_amount'])           
                    else:
                        # customers & sales invoices
                        match_customers = frappe.get_all("Customer", filters={'customer_name': party_name, 'disabled': 0}, fields=['name'])
                        if match_customers:
                            party_match = match_customers[0]['name']
                        # sales invoices
                        possible_sinvs = frappe.get_all("Sales Invoice", 
                            filters=[['outstanding_amount', '>', 0], ['docstatus', '=', 1]], 
                            fields=['name', 'customer', 'customer_name', 'outstanding_amount', 'esr_reference'])
                        if possible_sinvs:
                            invoice_matches = []
                            for sinv in possible_sinvs:
                                is_match = False
                                if sinv['name'] in transaction_reference or ('esr_reference' in sinv and sinv['esr_reference'] and sinv['esr_reference'] == transaction_reference):
                                    # matched exact sales invoice reference or ESR reference
                                    is_match = True
                                elif cint(settings.numeric_only_debtor_matching) == 1:
                                    # allow the numeric part matching
                                    if get_numeric_only_reference(sinv['name']) in transaction_reference: 
                                        # matched numeric part and customer name
                                        is_match = True

                                if is_match:
                                    invoice_matches.append(sinv['name'])
                                    # override party match in case there is one from the sales invoice
                                    party_match = sinv['customer']
                                    # add total matched amount
                                    matched_amount += float(sinv['outstanding_amount'])
                                        
                    # reset invoice matches in case there are no matches
                    try:
                        if len(invoice_matches) == 0:
                            invoice_matches = None
                        if len(expense_matches) == 0:
                            expense_matches = None                            
                    except:
                        pass                                                                                                
                    new_txn = {
                        'txid': len(txns),
                        'date': date,
                        'currency': currency,
                        'amount': amount,
                        'party_name': party_name,
                        'party_address': party_address,
                        'credit_debit': credit_debit,
                        'party_iban': party_iban,
                        'unique_reference': unique_reference,
                        'transaction_reference': transaction_reference,
                        'party_match': party_match,
                        'invoice_matches': invoice_matches,
                        'matched_amount': round(matched_amount, 2),
                        'employee_match': employee_match,
                        'expense_matches': expense_matches
                    }
                    txns.append(new_txn)
        else:
            # transaction without TxDtls: occurs at CS when transaction is from a pain.001 instruction
            # get unique ID
            try:
                unique_reference = entry_soup.acctsvcrref.get_text()
            except:
                # fallback: use tx id
                try:
                    unique_reference = entry_soup.txid.get_text()
                except:
                    # fallback to pmtinfid
                    try:
                        unique_reference = entry_soup.pmtinfid.get_text()
                    except:
                        # fallback to hash
                        code = "{0}:{1}:{2}".format(date, entry_currency, entry_amount)
                        unique_reference = hashlib.md5(code.encode("utf-8")).hexdigest()
            # check if this transaction is already recorded
            match_payment_entry = frappe.get_all('Payment Entry', filters={'reference_no': unique_reference}, fields=['name'])
            if match_payment_entry:
                if debug:
                    frappe.log_error("Transaction {0} is already imported in {1}.".format(unique_reference, match_payment_entry[0]['name']))
            else:
                # --- find transaction type: paid or received: (DBIT: paid, CRDT: received)
                credit_debit = entry_soup.cdtdbtind.get_text()
                # find payment instruction ID
                try:
                    payment_instruction_id = entry_soup.pmtinfid.get_text()     # instruction ID, PMTINF-[payment proposal]-row
                    payment_instruction_fields = payment_instruction_id.split("-")
                    payment_instruction_row = int(payment_instruction_fields[-1]) + 1
                    payment_proposal_id = payment_instruction_fields[1]
                    # find original instruction record
                    payment_proposal_payments = frappe.get_all("Payment Proposal Payment", 
                        filters={'parent': payment_proposal_id, 'idx': payment_instruction_row},
                        fields=['receiver', 'receiver_address_line1', 'receiver_address_line2', 'iban', 'reference'])
                    # suppliers 
                    party_match = None
                    if payment_proposal_payments:
                        match_suppliers = frappe.get_all("Supplier", filters={'supplier_name': payment_proposal_payments[0]['receiver']}, 
                            fields=['name'])
                        if match_suppliers:
                            party_match = match_suppliers[0]['name']
                    # purchase invoices 
                    invoice_match = None
                    matched_amount = 0
                    if payment_proposal_payments:
                        match_invoices = frappe.get_all("Purchase Invoice", 
                            filters=[['name', '=', payment_proposal_payments[0]['reference']], ['outstanding_amount', '>', 0]], 
                            fields=['name', 'grand_total'])
                        if match_invoices:
                            invoice_match = [match_invoices[0]['name']]
                            matched_amount = match_invoices[0]['grand_total']
                    if payment_proposal_payments:
                        new_txn = {
                            'txid': len(txns),
                            'date': date,
                            'currency': entry_currency,
                            'amount': entry_amount,
                            'party_name': payment_proposal_payments[0]['receiver'],
                            'party_address': "{0}, {1}".format(
                                payment_proposal_payments[0]['receiver_address_line1'], 
                                payment_proposal_payments[0]['receiver_address_line2']),
                            'credit_debit': credit_debit,
                            'party_iban': payment_proposal_payments[0]['iban'],
                            'unique_reference': unique_reference,
                            'transaction_reference': payment_proposal_payments[0]['reference'],
                            'party_match': party_match,
                            'invoice_matches': invoice_match,
                            'matched_amount': matched_amount
                        }
                        txns.append(new_txn)
                    else:
                        # not matched against payment instruction
                        new_txn = {
                            'txid': len(txns),
                            'date': date,
                            'currency': entry_currency,
                            'amount': entry_amount,
                            'party_name': "???",
                            'party_address': "???",
                            'credit_debit': credit_debit,
                            'party_iban': "???",
                            'unique_reference': unique_reference,
                            'transaction_reference': unique_reference,
                            'party_match': None,
                            'invoice_matches': None,
                            'matched_amount': None
                        }
                        txns.append(new_txn)
                except Exception as err:
                    # no payment instruction
                    new_txn = {
                        'txid': len(txns),
                        'date': date,
                        'currency': entry_currency,
                        'amount': entry_amount,
                        'party_name': "???",
                        'party_address': "???",
                        'credit_debit': credit_debit,
                        'party_iban': "???",
                        'unique_reference': unique_reference,
                        'transaction_reference': unique_reference,
                        'party_match': None,
                        'invoice_matches': None,
                        'matched_amount': None
                    }
                    txns.append(new_txn)

    return txns

@frappe.whitelist()
def make_payment_entry(amount, date, reference_no, paid_from=None, paid_to=None, type="Receive", 
    party=None, party_type=None, references=None, remarks=None, auto_submit=False, exchange_rate=1,
    party_iban=None, company=None):
    # assert list
    if references:
        references = ast.literal_eval(references)
    if str(auto_submit) == "1":
        auto_submit = True
    reference_type = "Sales Invoice"
    # find company
    if not company:
        if paid_from:
            company = frappe.get_value("Account", paid_from, "company")
        elif paid_to:
            company = frappe.get_value("Account", paid_to, "company")
    if type == "Receive":
        # receive
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Receive',
            'party_type': party_type,
            'party': party,
            'paid_to': paid_to,
            'paid_amount': float(amount),
            'received_amount': float(amount),
            'reference_no': reference_no,
            'reference_date': date,
            'posting_date': date,
            'remarks': remarks,
            'camt_amount': float(amount),
            'bank_account_no': party_iban,
            'company': company,
            'source_exchange_rate': exchange_rate,
            'target_exchange_rate': exchange_rate
        })
    elif type == "Pay":
        # pay
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Pay',
            'party_type': party_type,
            'party': party,
            'paid_from': paid_from,
            'paid_amount': float(amount),
            'received_amount': float(amount),
            'reference_no': reference_no,
            'reference_date': date,
            'posting_date': date,
            'remarks': remarks,
            'camt_amount': float(amount),
            'bank_account_no': party_iban,
            'company': company,
            'source_exchange_rate': exchange_rate,
            'target_exchange_rate': exchange_rate
        })
        if party_type == "Employee":
            reference_type = "Expense Claim"
        else:
            reference_type = "Purchase Invoice"
    else:
        # internal transfer (against intermediate account)
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Internal Transfer',
            'paid_from': paid_from,
            'paid_to': paid_to,
            'paid_amount': float(amount),
            'received_amount': float(amount),
            'reference_no': reference_no,
            'reference_date': date,
            'posting_date': date,
            'remarks': remarks,
            'camt_amount': float(amount),
            'bank_account_no': party_iban,
            'company': company,
            'source_exchange_rate': exchange_rate,
            'target_exchange_rate': exchange_rate
        })
    if party_type == "Employee":
        payment_entry.paid_to = get_payable_account(company, employee=True)['account'] or paid_to         # note: at creation, this is ignored
    new_entry = payment_entry.insert()
    # add references after insert (otherwise they are overwritten)
    if references:
        for reference in references:
            create_reference(new_entry.name, reference, reference_type)
    # automatically submit if enabled
    if auto_submit:
        matched_entry = frappe.get_doc("Payment Entry", new_entry.name)
        matched_entry.submit()
        frappe.db.commit()
    return get_url_to_form("Payment Entry", new_entry.name)

# creates the reference record in a payment entry
def create_reference(payment_entry, invoice_reference, invoice_type="Sales Invoice"):
    # create a new payment entry reference
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry.parent = payment_entry
    reference_entry.parentfield = "references"
    reference_entry.parenttype = "Payment Entry"
    reference_entry.reference_doctype = invoice_type
    reference_entry.reference_name = invoice_reference
    if "Invoice" in invoice_type:
        reference_entry.total_amount = frappe.get_value(invoice_type, invoice_reference, "base_grand_total")
        reference_entry.outstanding_amount = frappe.get_value(invoice_type, invoice_reference, "outstanding_amount")
        paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
        if paid_amount > reference_entry.outstanding_amount:
            reference_entry.allocated_amount = reference_entry.outstanding_amount
        else:
            reference_entry.allocated_amount = paid_amount
    else:
        # expense claim:
        reference_entry.total_amount = frappe.get_value(invoice_type, invoice_reference, "total_claimed_amount")
        reference_entry.outstanding_amount = reference_entry.total_amount
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

def get_numeric_only_reference(s):
    n = ""
    for c in s:
        if c.isdigit():
            n += c
    return n
