# -*- coding: utf-8 -*-
# Copyright (c) 2018-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
import time
import cgi          # used to escape xml content
from frappe import _
from frappe.utils.data import get_url_to_form

class DirectDebitProposal(Document):
    def validate(self):
        # check if closing on intermediate account that fields are set
        if self.use_intermediate == 1:
            if not self.intermediate_account:
                frappe.throw( _("Please provide an intermediate account.") )
            # if skonto applies, skonto fields are required
            for sinv in self.sales_invoices:
                if sinv.amount != sinv.outstanding_amount:
                    if not self.skonto_account or not self.skonto_cost_center:
                        frappe.throw( _("Please provide a skonto account and cost center.") )
    def on_submit(self):
        # clean payments (to prevent accumulation on re-submit)
        self.payments = {}
        # create the aggregated payment table
        # collect customers
        customers = []
        for sales_invoice in self.sales_invoices:
            if sales_invoice.customer not in customers:
                customers.append(sales_invoice.customer)
        # aggregate sales invoices
        for customer in customers:
            amount = 0
            references = []
            currency = ""
            for sales_invoice in self.sales_invoices:
                if sales_invoice.customer == customer:
                    amount += sales_invoice.amount
                    currency = sales_invoice.currency
                    references.append(sales_invoice.sales_invoice)
                    # mark sales invoices as proposed
                    invoice = frappe.get_doc("Sales Invoice", sales_invoice.sales_invoice)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        self.create_payment("Customer", customer, 
                            "Sales Invoice", sales_invoice.sales_invoice, datetime.now(),
                            sales_invoice.amount, sales_invoice.outstanding_amount)
            # add new payment record
            new_payment = self.append('payments', {})
            new_payment.customer = customer
            new_payment.amount = amount
            new_payment.currency = currency
            new_payment.reference = " ".join(references)

        # save
        self.save()

    def create_payment(self, party_type, party_name, 
                            reference_type, reference_name, date,
                            amount, outstanding_amount):
        # create new payment entry
        new_payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': "Receive",
            'party_type': party_type,
            'party': party_name,
            'posting_date': date,
            'paid_to': self.intermediate_account,
            'received_amount': amount,
            'paid_amount': amount,
            'reference_no': "{0} {1}".format(reference_name, self.name),
            'reference_date': date,
            'remarks': "From Direct Debit Proposal {0}".format(self.name),
            'references': [{ 
                'reference_doctype': reference_type,
                'reference_name': reference_name,
                'allocated_amount': amount,
                'due_date': date,
                'total_amount': amount,
                'outstanding_amount': amount
            }]
        })
        # in case of skonto deduction: consider deduction in payment entry
        if outstanding_amount != amount:
            new_payment_entry = frappe.get_doc({
                'doctype': 'Payment Entry',
                'payment_type': "Receive",
                'party_type': party_type,
                'party': party_name,
                'posting_date': date,
                'paid_to': self.intermediate_account,
                'received_amount': amount,
                'paid_amount': amount,
                'reference_no': "{0} {1}".format(reference_name, self.name),
                'reference_date': date,
                'remarks': "From Direct Debit Proposal {0}".format(self.name),
                'references': [{ 
                    'reference_doctype': reference_type,
                    'reference_name': reference_name,
                    'allocated_amount': outstanding_amount,
                    'due_date': date,
                    'total_amount': outstanding_amount,
                    'outstanding_amount': outstanding_amount
                }],
                'total_allocated_amount': outstanding_amount,
                'deductions': [{ 
                    'account': self.skonto_account,
                    'cost_center': self.skonto_cost_center,
                    'amount': (outstanding_amount - amount),
                }]
            })
        inserted_payment_entry = new_payment_entry.insert()
        inserted_payment_entry.submit()
        frappe.db.commit()
        return inserted_payment_entry
            
    def create_bank_file(self):
        # create xml header
        content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        # define xml template reference
        # load namespace based on banking region
        banking_region = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "banking_region")
        if banking_region == "AT":
            content += make_line("<Document xmlns=\"urn:iso:std:iso:20022:tech:xsd:pain.008.001.02\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"\">")
        else:
            content += make_line("<Document xmlns=\"http://www.six-interbank-clearing.com/de/pain.008.001.03.ch.02.xsd\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.six-interbank-clearing.com/de/pain.008.001.03.ch.02.xsd  pain.008.001.03.ch.02.xsd\">")
        # transaction holder
        content += make_line("  <CstmrDrctDbtInitn>")
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
        company_name = get_company_name(self.sales_invoices[0].sales_invoice)
        content += make_line("        <Nm>{0}</Nm>".format(cgi.escape(company_name)))
        content += make_line("      </InitgPty>")
        content += make_line("    </GrpHdr>")
        
        # get participation ID
        participation_number = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "participant_number")
        ### level B
        company_account = frappe.get_doc('Account', self.receive_to_account)
        content += make_line("    <PmtInf>")
        content += make_line("     <PmtInfId>{0}</PmtInfId>".format(self.name))
        content += make_line("     <PmtMtd>DD</PmtMtd>")
        content += make_line("     <PmtTpInf>")
        content += make_line("      <SvcLvl>")
        content += make_line("       <Cd>SEPA</Cd>")
        content += make_line("      </SvcLvl>")
        content += make_line("      <LclInstrm>")
        content += make_line("       <Cd>CORE</Cd>")
        content += make_line("      </LclInstrm>")
        content += make_line("      <SeqTp>RCUR</SeqTp>")
        content += make_line("     </PmtTpInf>")
        content += make_line("     <ReqdColltnDt>{0}</ReqdColltnDt>".format(self.date))
        content += make_line("     <Cdtr>")
        content += make_line("      <Nm>{0}</Nm>".format(cgi.escape(company_name)))
        content += make_line("     </Cdtr>")
        content += make_line("     <CdtrAcct>")
        content += make_line("      <Id>")
        content += make_line("       <IBAN>{0}</IBAN>".format(company_account.iban.replace(" ", "")))
        content += make_line("      </Id>")
        content += make_line("     </CdtrAcct>")
        content += make_line("     <CdtrAgt>")
        content += make_line("      <FinInstnId>")
        content += make_line("       <BIC>{0}</BIC>".format(company_account.bic))
        content += make_line("      </FinInstnId>")
        content += make_line("     </CdtrAgt>")
        content += make_line("     <ChrgBr>SLEV</ChrgBr>")
        
        # payments
        for payment in self.payments:
            transaction_count += 1
            customer = frappe.get_doc("Customer", payment.customer)
            content += make_line("<DrctDbtTxInf>")
            content += make_line(" <PmtId>")
            content += make_line("  <InstrId>SEPA1-{0}-{1}</InstrId>".format(self.date, transaction_count))
            content += make_line("  <EndToEndId>{0}-{1}</EndToEndId>".format(self.name, transaction_count))
            content += make_line(" </PmtId>")
            rounded_amount = round(payment.amount, 2)  # make sure there are no extra decimals, this would fail the validation
            content += make_line(" <InstdAmt Ccy=\"{0}\">{1}</InstdAmt>".format(payment.currency, rounded_amount))
            control_sum += rounded_amount
            content += make_line(" <DrctDbtTx>")
            content += make_line("  <MndtRltdInf>")
            content += make_line("   <MndtId>{0}</MndtId>".format(customer.lsv_code))
            content += make_line("   <DtOfSgntr>{0}</DtOfSgntr>".format(customer.lsv_date))
            content += make_line("   <AmdmntInd>false</AmdmntInd>")
            content += make_line("  </MndtRltdInf>")
            content += make_line("  <CdtrSchmeId>")
            content += make_line("   <Id>")
            content += make_line("    <PrvtId>")
            content += make_line("     <Othr>")
            content += make_line("      <Id>{0}</Id>".format(participation_number))
            content += make_line("      <SchmeNm>")
            content += make_line("       <Prtry>SEPA</Prtry>")
            content += make_line("      </SchmeNm>")
            content += make_line("     </Othr>")
            content += make_line("    </PrvtId>")
            content += make_line("   </Id>")
            content += make_line("  </CdtrSchmeId>")
            content += make_line(" </DrctDbtTx>")
            content += make_line(" <DbtrAgt>")
            content += make_line("  <FinInstnId>")
            content += make_line("    <BIC>{0}</BIC>".format(customer.bic))
            content += make_line("  </FinInstnId>")
            content += make_line(" </DbtrAgt>")
            content += make_line(" <Dbtr>")
            content += make_line("  <Nm>{0}</Nm>".format(cgi.escape(customer.customer_name)))
            content += make_line(" </Dbtr>")
            content += make_line(" <DbtrAcct>")
            content += make_line("  <Id>")
            content += make_line("   <IBAN>{0}</IBAN>".format(customer.iban.replace(" ", "")))
            content += make_line("  </Id>")
            content += make_line(" </DbtrAcct>")
            content += make_line(" <RmtInf>")
            content += make_line("  <Ustrd>{0}</Ustrd>".format(payment.reference))
            content += make_line(" </RmtInf>")
            content += make_line("</DrctDbtTxInf>")
      
        # add footer
        content += make_line("    </PmtInf>")
        content += make_line("  </CstmrDrctDbtInitn>")
        content += make_line("</Document>")
        # insert control numbers
        content = content.replace(transaction_count_identifier, "{0}".format(transaction_count))
        content = content.replace(control_sum_identifier, "{:.2f}".format(control_sum))
        
        return { 'content': content }
    pass

def get_company_name(sales_invoice):
    return frappe.get_value('Sales Invoice', sales_invoice, 'company')
    
# this function will create a new direct debit proposal
@frappe.whitelist()
def create_direct_debit_proposal(company=None):
    # check companies
    if company == None:
        companies = frappe.get_all("Company", filters={}, fields=['name'])
        company = companies[0]['name']
    # get all customers with open sales invoices
    sql_query = ("""SELECT `tabSales Invoice`.`customer` AS `customer`, 
              `tabSales Invoice`.`name` AS `name`,  
              `tabSales Invoice`.`outstanding_amount` AS `outstanding_amount`, 
              `tabSales Invoice`.`due_date` AS `due_date`, 
              `tabSales Invoice`.`currency` AS `currency`,
              (((100 - IFNULL(`tabPayment Terms Template`.`skonto_percent`, 0))/100) * `tabSales Invoice`.`outstanding_amount`) AS `skonto_amount`
            FROM `tabSales Invoice` 
            LEFT JOIN `tabPayment Terms Template` ON `tabSales Invoice`.`payment_terms_template` = `tabPayment Terms Template`.`name`
            WHERE `tabSales Invoice`.`docstatus` = 1 
              AND `tabSales Invoice`.`outstanding_amount` > 0
              AND `tabSales Invoice`.`enable_lsv` = 1
              AND `tabSales Invoice`.`is_proposed` = 0
              AND `tabSales Invoice`.`company` = '{0}';""".format(company))
    sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    new_record = None
    # get all sales invoices that are overdue
    if sales_invoices:
        now = datetime.now()
        invoices = []
        for invoice in sales_invoices:
            new_invoice = { 
                'customer': invoice.customer,
                'sales_invoice': invoice.name,
                'amount': invoice.skonto_amount, # formerly invoice.outstanding_amount, include skonto if applicable
                'outstanding_amount': invoice.outstanding_amount,
                'due_date': invoice.due_date,
                'currency': invoice.currency
            }
            invoices.append(new_invoice)
        # create new record
        new_proposal = frappe.get_doc({
            "doctype": "Direct Debit Proposal",
            "title": "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
            "date": "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
            "sales_invoices": invoices
        })
        proposal_record = new_proposal.insert()
        new_record = proposal_record.name
        frappe.db.commit()
    return get_url_to_form("Direct Debit Proposal", new_record) if new_record else None

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"


