from __future__ import unicode_literals

import frappe
from frappe import throw, _

def parse_ubs(content, account, auto_submit=False):
    # parse a ubs bank extract csv
    # collect all lines of the file
    #log("Starting parser...")
    lines = content.split("\n")
    # collect created payment entries
    new_payment_entries = []
    
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
                            new_payment_entry.party = "Guest"
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
                            new_payment_entry.party = "Guest"
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

def parse_cs(content, account, auto_submit=False):
    # parse a credit suisse bank extract csv
    # collect all lines of the file
    lines = content.split("\n")
    # collect created payment entries
    new_payment_entries = []
    
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
                            new_payment_entry.party = "Guest"
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
    date_parts = ch_date.split('.')
    return date_parts[2] + "-" + date_parts[1] + "-" + date_parts[0]

@frappe.whitelist()
def parse_file(content, bank, account, auto_submit=False):
    # content is the plain text content, parse 
    auto_submit = assert_bool(auto_submit);
   
    new_records = []
    if bank == "ubs":
        new_records = parse_ubs(content, account, auto_submit)
    elif bank == "zkb":
        new_records = parse_zkb(content, account, auto_submit)
    elif bank == "cs":
        new_records = parse_cs(content, account, auto_submit)
               
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
