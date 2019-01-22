# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
import time
from erpnextswiss.erpnextswiss.common_functions import get_building_number, get_street_name, get_pincode, get_city
import cgi          # used to escape xml content

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
            payment_type = "SEPA"
            # try executing in 30 days (will be reduced by actual due dates)
            exec_date = datetime.strptime(self.date, "%Y-%m-%d") + timedelta(days=30)
            for purchase_invoice in self.purchase_invoices:
                if purchase_invoice.supplier == supplier:
                    currency = purchase_invoice.currency
                    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    address = pinv.supplier_address
                    references.append(purchase_invoice.external_reference)
                    # find if skonto applies
                    if purchase_invoice.skonto_date:
                        skonto_date = datetime.strptime(purchase_invoice.skonto_date, "%Y-%m-%d")
                    due_date = datetime.strptime(purchase_invoice.due_date, "%Y-%m-%d")
                    if (purchase_invoice.skonto_date) and (skonto_date.date() >= datetime.now().date()):  
                        this_amount = purchase_invoice.skonto_amount    
                        if exec_date.date() > skonto_date.date():
                            exec_date = skonto_date
                    else:
                        this_amount = purchase_invoice.amount
                        if exec_date.date() > due_date.date():
                            exec_date = due_date
                    payment_type = purchase_invoice.payment_type
                    if payment_type == "ESR":
                        # run as individual payment (not aggregated)
                        supl = frappe.get_doc("Supplier", supplier)
                        addr = frappe.get_doc("Address", address)
                        self.add_payment(supl.supplier_name, supl.iban, payment_type,
                            addr.address_line1, "{0} {1}".format(addr.pincode, addr.city), addr.country,
                            this_amount, currency, " ".join(references), exec_date, 
                            purchase_invoice.esr_reference, purchase_invoice.esr_participation_number)
                    else:
                        amount += this_amount
                    # mark sales invoices as proposed
                    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        self.create_payment("Supplier", supplier, 
                            "Purchase Invoice", purchase_invoice.purchase_invoice, exec_date,
                            purchase_invoice.amount)
            # make sure execution date is valid
            if exec_date < datetime.now():
                exec_date = datetime.now()      # + timedelta(days=1)
            # add new payment record
            if amount > 0:
                supl = frappe.get_doc("Supplier", supplier)
                addr = frappe.get_doc("Address", address)
                self.add_payment(supl.supplier_name, supl.iban, payment_type,
                    addr.address_line1, "{0} {1}".format(addr.pincode, addr.city), addr.country,
                    amount, currency, " ".join(references), exec_date)
            
        # collect employees
        employees = []
        account_currency = frappe.get_value("Account", self.pay_from_account, 'account_currency')
        for expense_claim in self.expenses:
            if expense_claim.employee not in employees:
                employees.append(expense_claim.employee)
        # aggregate expense claims
        for employee in employees:
            amount = 0
            references = []
            currency = ""
            for expense_claim in self.expenses:
                if expense_claim.employee == employee:
                    amount += expense_claim.amount
                    currency = account_currency
                    references.append(expense_claim.expense_claim)
                    # mark expense claim as proposed
                    invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        self.create_payment("Employee", employee, 
                            "Expense Claim", expense_claim.expense_claim, exec_date,
                            expense_claim.amount)
            # add new payment record
            emp = frappe.get_doc("Employee", employee)
            address_lines = emp.permanent_address.split("\n")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(emp.employee_name, emp.bank_ac_no, "IBAN",
                address_lines[0], address_lines[1], cntry,
                amount, currency, " ".join(references), self.date)

        # save
        self.save()

    def on_cancel(self):
        # reset is_proposed
        for purchase_invoice in self.purchase_invoices:
            # un-mark sales invoices as proposed
            invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
            invoice.is_proposed = 0
            invoice.save()        
        for expense_claim in self.expenses:
            # un-mark expense claim as proposed
            invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
            invoice.is_proposed = 0
            invoice.save()               
        return
    
    def add_payment(self, receiver_name, iban, payment_type, address_line1, 
        address_line2, country, amount, currency, reference, execution_date, 
        esr_reference=None, esr_participation_number=None):
            new_payment = self.append('payments', {})
            new_payment.receiver = receiver_name
            new_payment.iban = iban
            new_payment.payment_type = payment_type
            new_payment.receiver_address_line1 = address_line1
            new_payment.receiver_address_line2 = address_line2
            new_payment.receiver_country = country           
            new_payment.amount = amount
            new_payment.currency = currency
            new_payment.reference = reference
            new_payment.execution_date = execution_date
            new_payment.esr_reference = esr_reference
            new_payment.esr_participation_number = esr_participation_number      
            return
    
    def create_payment(self, party_type, party_name, 
                            reference_type, reference_name, date,
                            amount):
        # create new payment entry
        new_payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': "Pay",
            'party_type': party_type,
            'party': party_name,
            'posting_date': date,
            'paid_from': self.intermediate_account,
            'received_amount': amount,
            'paid_amount': amount,
            'reference_no': reference_name,
            'reference_date': date,
            'remarks': "From Payment Proposal {0}".format(self.name),
            'references': [{ 
                'reference_doctype': reference_type,
                'reference_name': reference_name,
                'allocated_amount': amount,
                'due_date': date,
                'total_amount': amount,
                'outstanding_amount': amount
            }]
        })
        inserted_payment_entry = new_payment_entry.insert()
        inserted_payment_entry.submit()
        frappe.db.commit()
        return inserted_payment_entry
        
    def create_bank_file(self):
        #try:
            # create xml header
            content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
            # define xml template reference
            # load namespace based on banking region
            banking_region = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "banking_region")
            if banking_region == "AT":
                content += make_line("<Document xmlns=\"urn:iso:std:iso:20022:tech:xsd:pain.001.001.03\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"\">")
            else:
                content += make_line("<Document xmlns=\"http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd  pain.001.001.03.ch.02.xsd\">")
            # transaction holder
            content += make_line("  <CstmrCdtTrfInitn>")
            ### Group Header (GrpHdr, A-Level)
            # create group header
            content += make_line("    <GrpHdr>")
            # message ID (unique, SWIFT-characters only)
            content += make_line("      <MsgId>MSG-" + time.strftime("%Y%m%d%H%M%S") + "</MsgId>")
            # creation date and time ( e.g. 2010-02-15T07:30:00 )
            content += make_line("      <CreDtTm>" + time.strftime("%Y-%m-%dT%H:%M:%S") + "</CreDtTm>")
            # number of transactions in the file
            transaction_count = 0
            transaction_count_identifier = "<!-- $COUNT -->"
            content += make_line("      <NbOfTxs>" + transaction_count_identifier + "</NbOfTxs>")
            # total amount of all transactions ( e.g. 15850.00 )  (sum of all amounts)
            control_sum = 0.0
            control_sum_identifier = "<!-- $CONTROL_SUM -->"
            content += make_line("      <CtrlSum>" + control_sum_identifier + "</CtrlSum>")
            # initiating party requires at least name or identification
            content += make_line("      <InitgPty>")
            # initiating party name ( e.g. MUSTER AG )
            content += make_line("        <Nm>" + cgi.escape(self.company) + "</Nm>")
            content += make_line("      </InitgPty>")
            content += make_line("    </GrpHdr>")
            
            ### Payment Information (PmtInf, B-Level)
            # payment information records (1 .. 99'999)
            for payment in self.payments:
                # create temporary code block to compile the payment record (only add to overall on submit)
                # use 'continue' to skip a record (in case a validation fails)
                payment_content = ""
                # create the payment entries
                payment_content += make_line("    <PmtInf>")
                # unique (in this file) identification for the payment ( e.g. PMTINF-01, PMTINF-PE-00005 )
                payment_content += make_line("      <PmtInfId>PMTINF-{0}-{1}</PmtInfId>".format(self.name, transaction_count))
                # payment method (TRF or TRA, no impact in Switzerland)
                payment_content += make_line("      <PmtMtd>TRF</PmtMtd>")
                # batch booking (true or false; recommended true)
                payment_content += make_line("      <BtchBookg>true</BtchBookg>")
                # Requested Execution Date (e.g. 2010-02-22, remove time element)
                payment_content += make_line("      <ReqdExctnDt>{0}</ReqdExctnDt>".format(
                    payment.execution_date.split(" ")[0]))
                # debitor (technically ignored, but recommended)   
                payment_content += make_line("      <Dbtr>")
                # debitor name
                payment_content += make_line("        <Nm>{0}</Nm>".format(cgi.escape(self.company)))
                # postal address (recommendadtion: do not use)
                #content += make_line("        <PstlAdr>")
                #content += make_line("          <Ctry>CH</Ctry>")
                #content += make_line("          <AdrLine>SELDWYLA</AdrLine>")
                #content += make_line("        </PstlAdr>")
                payment_content += make_line("      </Dbtr>")
                # debitor account (sender) - IBAN
                payment_account = frappe.get_doc('Account', self.pay_from_account)
                payment_content += make_line("      <DbtrAcct>")
                payment_content += make_line("        <Id>")
                if payment_account.iban:
                    payment_content += make_line("          <IBAN>{0}</IBAN>".format(
                        payment_account.iban.replace(" ", "") ))
                else:
                    # no paying account IBAN: not valid record, skip
                    frappe.throw( _("{0}: no account IBAN found ({1})".format(
                        payment.references, self.pay_from_account) ) )
                payment_content += make_line("        </Id>")
                payment_content += make_line("      </DbtrAcct>")
                if payment_account.bic:
                    # debitor agent (sender) - BIC
                    payment_content += make_line("      <DbtrAgt>")
                    payment_content += make_line("        <FinInstnId>")
                    payment_content += make_line("          <BIC>{0}</BIC>".format(payment_account.bic))
                    payment_content += make_line("        </FinInstnId>")
                    payment_content += make_line("      </DbtrAgt>")
                    
                ### Credit Transfer Transaction Information (CdtTrfTxInf, C-Level)
                payment_content += make_line("      <CdtTrfTxInf>")
                # payment identification
                payment_content += make_line("        <PmtId>")
                # instruction identification 
                payment_content += make_line("          <InstrId>INSTRID-{0}-{1}</InstrId>".format(self.name, transaction_count))
                # end-to-end identification (should be used and unique within B-level; payment entry name)
                payment_content += make_line("          <EndToEndId>{0}</EndToEndId>".format(payment.reference))
                payment_content += make_line("        </PmtId>")
                # payment type information
                payment_content += make_line("        <PmtTpInf>")
                # service level: only used for SEPA (currently not implemented)
                if payment.payment_type == "SEPA":
                    payment_content += make_line("          <SvcLvl>")
                    # service level code (e.g. SEPA)
                    payment_content += make_line("            <Cd>SEPA</Cd>")
                    payment_content += make_line("          </SvcLvl>")
                # local instrument
                if payment.payment_type == "ESR":
                    payment_content += make_line("          <LclInstrm>")
                    # proprietary (nothing or CH01 for ESR)        
                    payment_content += make_line("            <Prtry>CH01</Prtry>")
                    payment_content += make_line("          </LclInstrm>")        
                payment_content += make_line("        </PmtTpInf>")
                # amount 
                payment_content += make_line("        <Amt>")
                payment_content += make_line("          <InstdAmt Ccy=\"{0}\">{1:.2f}</InstdAmt>".format(
                    payment.currency,
                    payment.amount))
                payment_content += make_line("        </Amt>")
                # creditor account
                # creditor account identification
                if payment.payment_type == "ESR":
                    # add creditor information
                    creditor_info = self.add_creditor_info(payment)
                    if creditor_info:
                        payment_content += creditor_info
                    else:
                        # no address found, skip entry (not valid)
                        content += add_invalid_remark( _("{0}: no address (or country) found").format(payment) )
                        skipped.append(payment)
                        continue
                    # ESR payment
                    payment_content += make_line("        <CdtrAcct>")
                    payment_content += make_line("          <Id>")
                    payment_content += make_line("            <Othr>")
                    # ESR participant number
                    if payment.esr_participation_number:
                        payment_content += make_line("              <Id>" +
                            payment.esr_participation_number + "</Id>")
                    else:
                        # no particpiation number: not valid record, skip
                        frappe.throw( _("{0}: no ESR participation number found").format(payment) )
                    payment_content += make_line("            </Othr>")
                    payment_content += make_line("          </Id>")
                    payment_content += make_line("        </CdtrAcct>")
                    # Remittance Information
                    payment_content += make_line("        <RmtInf>")
                    payment_content += make_line("          <Strd>")
                    # Creditor Reference Information
                    payment_content += make_line("            <CdtrRefInf>")
                    # ESR reference 
                    if payment.esr_reference:
                        payment_content += make_line("              <Ref>" +
                            payment.esr_reference.replace(" ", "") + "</Ref>")
                    else:
                        # no ESR reference: not valid record, skip
                        frappe.throw( _("{0}: no ESR reference found").format(payment) )
                    payment_content += make_line("            </CdtrRefInf>")
                    payment_content += make_line("          </Strd>")
                    payment_content += make_line("        </RmtInf>")
                else:
                    # IBAN or SEPA payment
                    # add creditor information
                    creditor_info = self.add_creditor_info(payment)
                    if creditor_info:
                        payment_content += creditor_info
                    else:
                        # no address found, skip entry (not valid)
                        self.throw( _("{0}: no address (or country) found").format(payment) )
                    # creditor agent (BIC, optional; removed to resolve issue #15)
                    #if payment_record.bic:                
                    #    payment_content += make_line("        <CdtrAgt>")
                    #    payment_content += make_line("          <FinInstnId>")
                    #    payment_content += make_line("            <BIC>" + 
                    #        payment_record.bic + "</BIC>")
                    #    payment_content += make_line("          </FinInstnId>")
                    #    payment_content += make_line("        </CdtrAgt>")    
                    # creditor account
                    payment_content += make_line("        <CdtrAcct>")
                    payment_content += make_line("          <Id>")
                    if payment.iban:
                        payment_content += make_line("            <IBAN>{0}</IBAN>".format( 
                            payment.iban.replace(" ", "") ))
                    else:
                        # no iban: not valid record, skip
                        frappe.throw( _("{0}: no IBAN found").format(payment) )
                    payment_content += make_line("          </Id>")
                    payment_content += make_line("        </CdtrAcct>")
                    # Remittance Information
                    payment_content += make_line("        <RmtInf>")
                    payment_content += make_line("          <Ustrd>{0}</Ustrd>".format(payment.reference))
                    payment_content += make_line("        </RmtInf>")
                                            
                # close payment record
                payment_content += make_line("      </CdtTrfTxInf>")
                payment_content += make_line("    </PmtInf>")
                # once the payment is extracted for payment, submit the record
                transaction_count += 1
                control_sum += payment.amount
                content += payment_content
            # add footer
            content += make_line("  </CstmrCdtTrfInitn>")
            content += make_line("</Document>")
            # insert control numbers
            content = content.replace(transaction_count_identifier, "{0}".format(transaction_count))
            content = content.replace(control_sum_identifier, "{:.2f}".format(control_sum))
            
            return { 'content': content }
        
        #except IndexError:
        #    frappe.msgprint( _("Please select at least one payment."), _("Information") )
        #    return
        #except:
        #    frappe.throw( _("Error while generating xml. Make sure that you made required customisations to the DocTypes.") )
        #    return
    
    def add_creditor_info(self, payment):
        payment_content = ""
        # creditor information
        payment_content += make_line("        <Cdtr>") 
        # name of the creditor/supplier
        payment_content += make_line("          <Nm>" + cgi.escape(payment.receiver)  + "</Nm>")
        # address of creditor/supplier (should contain at least country and first address line
        payment_content += make_line("          <PstlAdr>")
        # street name
        payment_content += make_line("            <StrtNm>{0}</StrtNm>".format(cgi.escape(get_street_name(payment.receiver_address_line1))))
        # building number
        payment_content += make_line("            <BldgNb>{0}</BldgNb>".format(cgi.escape(get_building_number(payment.receiver_address_line1))))
        # postal code
        payment_content += make_line("            <PstCd>{0}</PstCd>".format(cgi.escape(get_pincode(payment.receiver_address_line2))))
        # town name
        payment_content += make_line("            <TwnNm>{0}</TwnNm>".format(cgi.escape(get_city(payment.receiver_address_line2))))
        country = frappe.get_doc("Country", payment.receiver_country)
        payment_content += make_line("            <Ctry>" + country.code.upper() + "</Ctry>")
        payment_content += make_line("          </PstlAdr>")
        payment_content += make_line("        </Cdtr>") 
        return payment_content

# this function will create a new payment proposal
@frappe.whitelist()
def create_payment_proposal(date=None, company=None):
    if not date:
        # get planning days
        planning_days = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'planning_days')
        date = datetime.now() + timedelta(days=planning_days) 
        if not planning_days:
            frappe.throw( "Please configure the planning period in ERPNextSwiss Settings.")
    # check companies (take first created if none specififed)
    if company == None:
        companies = frappe.get_all("Company", filters={}, fields=['name'], order_by='creation')
        company = companies[0]['name']
    # get all suppliers with open purchase invoices
    sql_query = ("""SELECT 
                  `tabPurchase Invoice`.`supplier` AS `supplier`, 
                  `tabPurchase Invoice`.`name` AS `name`,  
                  `tabPurchase Invoice`.`outstanding_amount` AS `outstanding_amount`, 
                  `tabPurchase Invoice`.`due_date` AS `due_date`, 
                  `tabPurchase Invoice`.`currency` AS `currency`,
                  `tabPurchase Invoice`.`bill_no` AS `external_reference`,
                  (IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, `tabPurchase Invoice`.`due_date`, (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)))) AS `skonto_date`,
                  (((100 - IFNULL(`tabPayment Terms Template`.`skonto_percent`, 0))/100) * `tabPurchase Invoice`.`outstanding_amount`) AS `skonto_amount`,
                  `tabPurchase Invoice`.`payment_type` AS `payment_type`,
                  `tabPurchase Invoice`.`esr_reference_number` AS `esr_reference`,
                  `tabSupplier`.`esr_participation_number` AS `esr_participation_number`
                FROM `tabPurchase Invoice` 
                LEFT JOIN `tabPayment Terms Template` ON `tabPurchase Invoice`.`payment_terms_template` = `tabPayment Terms Template`.`name`
                LEFT JOIN `tabSupplier` ON `tabPurchase Invoice`.`supplier` = `tabSupplier`.`name`
                WHERE `tabPurchase Invoice`.`docstatus` = 1 
                  AND `tabPurchase Invoice`.`outstanding_amount` > 0
                  AND ((`tabPurchase Invoice`.`due_date` <= '{date}') 
                    OR ((IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, `tabPurchase Invoice`.`due_date`, (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)))) <= '{date}'))
                  AND `tabPurchase Invoice`.`is_proposed` = 0
                  AND `tabPurchase Invoice`.`company` = '{company}';""".format(date=date, company=company))
    purchase_invoices = frappe.db.sql(sql_query, as_dict=True)
    # get all purchase invoices that pending
    invoices = []
    for invoice in purchase_invoices:
        reference = invoice.external_reference or invoice.name
        new_invoice = { 
            'supplier': invoice.supplier,
            'purchase_invoice': invoice.name,
            'amount': invoice.outstanding_amount,
            'due_date': invoice.due_date,
            'currency': invoice.currency,
            'skonto_date': invoice.skonto_date,
            'skonto_amount': invoice.skonto_amount,
            'payment_type': invoice.payment_type,
            'esr_reference': invoice.esr_reference,
            'esr_participation_number': invoice.esr_participation_number,
            'external_reference': reference
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
                  AND `is_proposed` = 0
                  AND `company` = '{company}';""".format(company=company))
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
        'expenses': expenses
    })
    proposal_record = new_proposal.insert()
    new_record = proposal_record.name
    frappe.db.commit()
    return new_record

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"
