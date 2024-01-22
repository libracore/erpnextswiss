# -*- coding: utf-8 -*-
# Copyright (c) 2017-2023, libracore (https://www.libracore.com) and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import time
from erpnextswiss.erpnextswiss.common_functions import get_building_number, get_street_name, get_pincode, get_city
import html              # used to escape xml content

@frappe.whitelist()
def get_payments():
    payments = frappe.get_list('Payment Entry', 
        filters={'docstatus': 0, 'payment_type': 'Pay'}, 
        fields=['name', 'posting_date', 'paid_amount', 'party', 'paid_from', 'paid_to_account_currency'], 
        order_by='posting_date')
    
    return { 'payments': payments }

@frappe.whitelist()
def generate_payment_file(payments):
    # creates a pain.001 payment file from the selected payments

    try:
        # convert JavaScript parameter into Python array
        payments = eval(payments)
        # remove empty items in case there should be any (bigfix for issue #2)
        payments = list(filter(None, payments))
        
        # array for skipped payments
        skipped = []
        
        # create xml header
        content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        # define xml template reference
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
        content += make_line("        <Nm>" + get_company_name(payments[0]) + "</Nm>")
        content += make_line("      </InitgPty>")
        content += make_line("    </GrpHdr>")
        
        ### Payment Information (PmtInf, B-Level)
        # payment information records (1 .. 99'999)
        for payment in payments:
            # create temporary code block to compile the payment record (only add to overall on submit)
            # use 'continue' to skip a record (in case a validation fails)
            payment_content = ""
            # retrieve the payment entry record
            payment_record = frappe.get_doc('Payment Entry', payment)
            # create the payment entries
            payment_content += make_line("    <PmtInf>")
            # unique (in this file) identification for the payment ( e.g. PMTINF-01, PMTINF-PE-00005 )
            payment_content += make_line("      <PmtInfId>PMTINF-" + payment + "</PmtInfId>")
            # payment method (TRF or TRA, no impact in Switzerland)
            payment_content += make_line("      <PmtMtd>TRF</PmtMtd>")
            # batch booking (true or false; recommended true)
            payment_content += make_line("      <BtchBookg>true</BtchBookg>")
            # Requested Execution Date (e.g. 2010-02-22)
            payment_content += make_line("      <ReqdExctnDt>{0}</ReqdExctnDt>".format(
                payment_record.posting_date))
            # debitor (technically ignored, but recommended)   
            payment_content += make_line("      <Dbtr>")
            # debitor name
            payment_content += make_line("        <Nm>" +
                cgi.escape(payment_record.company) + "</Nm>")
            # postal address (recommendadtion: do not use)
            #content += make_line("        <PstlAdr>")
            #content += make_line("          <Ctry>CH</Ctry>")
            #content += make_line("          <AdrLine>SELDWYLA</AdrLine>")
            #content += make_line("        </PstlAdr>")
            payment_content += make_line("      </Dbtr>")
            # debitor account (sender) - IBAN
            payment_account = frappe.get_doc('Account', payment_record.paid_from)
            payment_content += make_line("      <DbtrAcct>")
            payment_content += make_line("        <Id>")
            if payment_account.iban:
                payment_content += make_line("          <IBAN>{0}</IBAN>".format(
                    payment_account.iban.replace(" ", "") ))
            else:
                # no paying account IBAN: not valid record, skip
                content += add_invalid_remark( _("{0}: no account IBAN found ({1})".format(
                    payment, payment_record.paid_from) ) )
                skipped.append(payment)
                continue
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
            payment_content += make_line("          <InstrId>INSTRID-" + payment + "</InstrId>")
            # end-to-end identification (should be used and unique within B-level; payment entry name)
            payment_content += make_line("          <EndToEndId>" + payment + "</EndToEndId>")
            payment_content += make_line("        </PmtId>")
            # payment type information
            payment_content += make_line("        <PmtTpInf>")
            # service level: only used for SEPA (currently not implemented)
            if payment_record.transaction_type == "SEPA":
                payment_content += make_line("          <SvcLvl>")
                # service level code (e.g. SEPA)
                payment_content += make_line("            <Cd>SEPA</Cd>")
                payment_content += make_line("          </SvcLvl>")
            # local instrument
            if payment_record.transaction_type == "ESR":
                payment_content += make_line("          <LclInstrm>")
                # proprietary (nothing or CH01 for ESR)        
                payment_content += make_line("            <Prtry>CH01</Prtry>")
                payment_content += make_line("          </LclInstrm>")        
            payment_content += make_line("        </PmtTpInf>")
            # amount 
            payment_content += make_line("        <Amt>")
            payment_content += make_line("          <InstdAmt Ccy=\"{0}\">{1:.2f}</InstdAmt>".format(
                payment_record.paid_from_account_currency,
                payment_record.paid_amount))
            payment_content += make_line("        </Amt>")
            # creditor account
            # creditor account identification
            if payment_record.transaction_type == "ESR":
                # add creditor information
                creditor_info = add_creditor_info(payment_record)
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
                if payment_record.esr_participant_number:
                    payment_content += make_line("              <Id>" +
                        payment_record.esr_participant_number + "</Id>")
                else:
                    # no particpiation number: not valid record, skip
                    content += add_invalid_remark( _("{0}: no ESR participation number found").format(payment) )
                    skipped.append(payment)
                    continue
                payment_content += make_line("            </Othr>")
                payment_content += make_line("          </Id>")
                payment_content += make_line("        </CdtrAcct>")
                # Remittance Information
                payment_content += make_line("        <RmtInf>")
                payment_content += make_line("          <Strd>")
                # Creditor Reference Information
                payment_content += make_line("            <CdtrRefInf>")
                # ESR reference 
                if payment_record.esr_reference:
                    payment_content += make_line("              <Ref>" +
                        payment_record.esr_reference.replace(" ", "") + "</Ref>")
                else:
                    # no ESR reference: not valid record, skip
                    content += add_invalid_remark( _("{0}: no ESR reference found").format(payment) )
                    skipped.append(payment)
                    continue    
                payment_content += make_line("            </CdtrRefInf>")
                payment_content += make_line("          </Strd>")
                payment_content += make_line("        </RmtInf>")
            else:
                # IBAN or SEPA payment
                # add creditor information
                creditor_info = add_creditor_info(payment_record)
                if creditor_info:
                    payment_content += creditor_info
                else:
                    # no address found, skip entry (not valid)
                    content += add_invalid_remark( _("{0}: no address (or country) found").format(payment) )
                    skipped.append(payment)
                    continue
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
                if payment_record.iban:
                    payment_content += make_line("            <IBAN>{0}</IBAN>".format( 
                        payment_record.iban.replace(" ", "") ))
                else:
                    # no iban: not valid record, skip
                    content += add_invalid_remark( _("{0}: no IBAN found").format(payment) )
                    skipped.append(payment)
                    continue
                payment_content += make_line("          </Id>")
                payment_content += make_line("        </CdtrAcct>")
                                        
            # close payment record
            payment_content += make_line("      </CdtTrfTxInf>")
            payment_content += make_line("    </PmtInf>")
            # once the payment is extracted for payment, submit the record
            transaction_count += 1
            control_sum += payment_record.paid_amount
            content += payment_content
            payment_record.submit()
        # add footer
        content += make_line("  </CstmrCdtTrfInitn>")
        content += make_line("</Document>")
        # insert control numbers
        content = content.replace(transaction_count_identifier, "{0}".format(transaction_count))
        content = content.replace(control_sum_identifier, "{:.2f}".format(control_sum))
        
        return { 'content': content, 'skipped': skipped }
    except IndexError:
        frappe.msgprint( _("Please select at least one payment."), _("Information") )
        return
    except:
        frappe.throw( _("Error while generating xml. Make sure that you made required customisations to the DocTypes.") )
        return

def add_creditor_info(payment_record):
    payment_content = ""
    # creditor information
    payment_content += make_line("        <Cdtr>") 
    # name of the creditor/supplier
    name = payment_record.party
    if payment_record.party_type == "Employee":
        name = frappe.get_value("Employee", payment_record.party, "employee_name")
    payment_content += make_line("          <Nm>" + name  + "</Nm>")
    # address of creditor/supplier (should contain at least country and first address line
    # get supplier address
    if payment_record.party_type == "Supplier" or payment_record.party_type == "Customer":
        supplier_address = get_billing_address(payment_record.party, payment_record.party_type)
        if supplier_address == None:
            return None
        street = get_street_name(supplier_address.address_line1)
        building = get_building_number(supplier_address.address_line1)
        plz = supplier_address.pincode
        city = supplier_address.city 
        # country (has to be a two-digit code)
        try:
            country_code = frappe.get_value('Country', supplier_address.country, 'code').upper()
        except:
            country_code = "CH"
    elif payment_record.party_type == "Employee":
        employee = frappe.get_doc("Employee", payment_record.party)
        if employee.permanent_address:
           address = employee.permanent_address
        elif employee.current_address:
            address = employee.current_address
        else:
            # no address found
            return None
        try:
            lines = address.split("\n")
            street = get_street_name(lines[0])
            building = get_building_number(lines[0])
            plz = get_pincode(lines[1])
            city = get_city(lines[1])
            country_code = "CH"                
        except:
            # invalid address
            return None
    else:
        # unknown supplier type
        return None
    payment_content += make_line("          <PstlAdr>")
    # street name
    payment_content += make_line("            <StrtNm>" + street + "</StrtNm>")
    # building number
    payment_content += make_line("            <BldgNb>" + building + "</BldgNb>")
    # postal code
    payment_content += make_line("            <PstCd>{0}</PstCd>".format(plz))
    # town name
    payment_content += make_line("            <TwnNm>" + city + "</TwnNm>")
    payment_content += make_line("            <Ctry>" + country_code + "</Ctry>")
    payment_content += make_line("          </PstlAdr>")
    payment_content += make_line("        </Cdtr>") 
    return payment_content
            
def get_total_amount(payments):
    # get total amount from all payments
    total_amount = float(0)
    for payment in payments:
        payment_amount = frappe.get_value('Payment Entry', payment, 'paid_amount')
        total_amount += payment_amount
        
    return total_amount

def get_company_name(payment_entry):
    return frappe.get_value('Payment Entry', payment_entry, 'company')

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"

# add a remark if a payment entry was skipped
def add_invalid_remark(remark):
    return make_line("    <!-- " + remark + " -->")
    
# try to find the optimal billing address
def get_billing_address(supplier_name, supplier_type="Supplier"):
    if supplier_type == "Customer":
        linked_addresses = frappe.get_all('Dynamic Link', 
        filters={
            'link_doctype': 'customer', 
            'link_name': supplier_name, 
            'parenttype': 'Address'
        }, 
        fields=['parent'])         
    else:
        linked_addresses = frappe.get_all('Dynamic Link', 
        filters={
            'link_doctype': 'supplier', 
            'link_name': supplier_name, 
            'parenttype': 'Address'
        }, 
        fields=['parent'])     
    if len(linked_addresses) > 0:
        if len(linked_addresses) > 1:
            for address_name in linked_addresses:
                address = frappe.get_doc('Address', address_name)            
                if address.address_type == "Billing":
                    # this is a billing address, keep as option
                    billing_address = address
                    if address.is_primary_address == 1:
                        # this is the primary billing address
                        return address
                if address.is_primary_address == 1:
                    # this is a primary but not billing address
                    primary_address = address
            # evaluate best address found
            if billing_address:
                # found one or more billing address (but no primary)
                return billing_address
            elif primary_address:
                # found no billing but a primary address
                return primary_address
            else:
                # found neither billing nor a primary address
                return frappe.get_doc('Address', linked_addresses[0].parent)
        else:
            # return the one (and only) address 
            return frappe.get_doc('Address', linked_addresses[0].parent)
    else:
        # no address found
        return None

@frappe.whitelist()
def generate_payment_file_from_payroll(payroll_entry):
    payroll_record = frappe.get_doc("Payroll Entry", payroll_entry)
    payments = []
    # note: find by matching time range as there is a known issue that the link does not work (v10)
    salary_slips = frappe.get_all("Salary Slip",
        filters={'start_date': payroll_record.start_date,
            'end_date': payroll_record.end_date,
            'docstatus': 1
        }, fields=['name', 'posting_date', 'rounded_total', 'employee_name', 'employee', 'bank_account_no'])
    company = frappe.get_doc('Company', payroll_record.company)
    country_code = frappe.get_value("Country", company.country, 'code').upper()
    for salary_slip in salary_slips:
        # collect address information
        employee = frappe.get_doc("Employee", salary_slip['employee'])
        if employee.permanent_address:
           address = employee.permanent_address
        elif employee.current_address:
            address = employee.current_address
        else:
            frappe.throw( _("No address for employee {0} found.").format(salary_slip['employee_name']) )
        lines = address.split("\n")
        street = get_street_name(lines[0])
        building = get_building_number(lines[0])
        pincode = get_pincode(lines[1])
        city = get_city(lines[1])
            
        payments.append({
            'payment_id': cgi.escape("PMTINF-{0}".format(salary_slip['name'])),
            'execution_date': salary_slip['posting_date'],
            'instruction_id': cgi.escape("INSTRID-{0}".format(salary_slip['name'])),
            'endtoend_id': cgi.escape("{0}".format(salary_slip['name'])),
            'transaction_type': "SEPA",
            'amount': salary_slip['rounded_total'],
            'currency': company.default_currency,
            'receiver_name': cgi.escape(salary_slip['employee_name']),
            'receiver_street': cgi.escape(street),
            'receiver_building': cgi.escape(building),
            'receiver_city': cgi.escape(city),
            'receiver_pincode': cgi.escape(pincode),
            'receiver_country': country_code,
            'receiver_iban': salary_slip['bank_account_no'].replace(" ", "")
        })
    try:
        paid_from = frappe.get_value('Account', payroll_record.payment_account, 'iban').replace(" ", "")
    except:
        frappe.throw("Account IBAN not found: {0}".format(payroll_record.payment_account))
            
    pain001_data = {
        'msg_id': "MSG-" + payroll_record.name,
        'company': cgi.escape(payroll_record.company),
        'payments': payments,
        'paid_from_iban': paid_from,
        'paid_from_bic': frappe.get_value('Account', payroll_record.payment_account, 'bic')
    }
    return generate_pain001(pain001_data)
    
def generate_pain001(pain001_data):
    # creates a pain.001 payment file from a payroll
    #try:       
        # array for skipped payments
        skipped = []
        
        # create xml header
        content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        # define xml template reference
        content += make_line("<Document xmlns=\"http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd  pain.001.001.03.ch.02.xsd\">")
        # transaction holder
        content += make_line("  <CstmrCdtTrfInitn>")
        ### Group Header (GrpHdr, A-Level)
        # create group header
        content += make_line("    <GrpHdr>")
        # message ID (unique, SWIFT-characters only)
        content += make_line("      <MsgId>{0}</MsgId>".format(pain001_data['msg_id']))
        # creation date and time ( e.g. 2010-02-15T07:30:00 )
        content += make_line("      <CreDtTm>{0}</CreDtTm>".format(time.strftime("%Y-%m-%dT%H:%M:%S")))
        # number of transactions in the file
        transaction_count = 0
        transaction_count_identifier = "<!-- $COUNT -->"
        content += make_line("      <NbOfTxs>{0}</NbOfTxs>".format(transaction_count_identifier))
        # total amount of all transactions ( e.g. 15850.00 )  (sum of all amounts)
        control_sum = 0.0
        control_sum_identifier = "<!-- $CONTROL_SUM -->"
        content += make_line("      <CtrlSum>{0}</CtrlSum>".format(control_sum_identifier))
        # initiating party requires at least name or identification
        content += make_line("      <InitgPty>")
        # initiating party name ( e.g. MUSTER AG )
        content += make_line("        <Nm>{0}</Nm>".format(pain001_data['company']))
        content += make_line("      </InitgPty>")
        content += make_line("    </GrpHdr>")
        
        ### Payment Information (PmtInf, B-Level)
        # payment information records (1 .. 99'999)
        for payment in pain001_data['payments']:
            # create temporary code block to compile the payment record (only add to overall on submit)
            # use 'continue' to skip a record (in case a validation fails)
            payment_content = ""
            # create the payment entries
            payment_content += make_line("    <PmtInf>")
            # unique (in this file) identification for the payment ( e.g. PMTINF-01, PMTINF-PE-00005 )
            payment_content += make_line("      <PmtInfId>{0}</PmtInfId>".format(payment['payment_id']))
            # payment method (TRF or TRA, no impact in Switzerland)
            payment_content += make_line("      <PmtMtd>TRF</PmtMtd>")
            # batch booking (true or false; recommended true)
            payment_content += make_line("      <BtchBookg>true</BtchBookg>")
            # Requested Execution Date (e.g. 2010-02-22)
            payment_content += make_line("      <ReqdExctnDt>{0}</ReqdExctnDt>".format(
                payment['execution_date']))
            # debitor (technically ignored, but recommended)   
            payment_content += make_line("      <Dbtr>")
            # debitor name
            payment_content += make_line("        <Nm>{0}</Nm>".format(pain001_data['company']))
            # postal address (recommendadtion: do not use)
            #content += make_line("        <PstlAdr>")
            #content += make_line("          <Ctry>CH</Ctry>")
            #content += make_line("          <AdrLine>SELDWYLA</AdrLine>")
            #content += make_line("        </PstlAdr>")
            payment_content += make_line("      </Dbtr>")
            # debitor account (sender) - IBAN
            payment_content += make_line("      <DbtrAcct>")
            payment_content += make_line("        <Id>")
            if pain001_data['paid_from_iban']:
                payment_content += make_line("          <IBAN>{0}</IBAN>".format(
                    pain001_data['paid_from_iban'].replace(" ", "") ))
            else:
                # no paying account IBAN: not valid record, skip
                content += add_invalid_remark( _("{0}: no account IBAN found ({1})".format(
                    payment, payment_record.paid_from) ) )
                skipped.append(payment)
                continue
            payment_content += make_line("        </Id>")
            payment_content += make_line("      </DbtrAcct>")
            if pain001_data['paid_from_bic']:
                # debitor agent (sender) - BIC
                payment_content += make_line("      <DbtrAgt>")
                payment_content += make_line("        <FinInstnId>")
                payment_content += make_line("          <BIC>{0}</BIC>".format(pain001_data['paid_from_bic']))
                payment_content += make_line("        </FinInstnId>")
                payment_content += make_line("      </DbtrAgt>")
                
            ### Credit Transfer Transaction Information (CdtTrfTxInf, C-Level)
            payment_content += make_line("      <CdtTrfTxInf>")
            # payment identification
            payment_content += make_line("        <PmtId>")
            # instruction identification 
            payment_content += make_line("          <InstrId>{0}</InstrId>".format(payment['instruction_id']))
            # end-to-end identification (should be used and unique within B-level; payment entry name)
            payment_content += make_line("          <EndToEndId>{0}</EndToEndId>".format(payment['endtoend_id']))
            payment_content += make_line("        </PmtId>")
            # payment type information
            payment_content += make_line("        <PmtTpInf>")
            # service level: only used for SEPA (currently not implemented)
            if payment['transaction_type'] == "SEPA":
                payment_content += make_line("          <SvcLvl>")
                # service level code (e.g. SEPA)
                payment_content += make_line("            <Cd>SEPA</Cd>")
                payment_content += make_line("          </SvcLvl>")
            # local instrument
            if payment['transaction_type'] == "ESR":
                payment_content += make_line("          <LclInstrm>")
                # proprietary (nothing or CH01 for ESR)        
                payment_content += make_line("            <Prtry>CH01</Prtry>")
                payment_content += make_line("          </LclInstrm>")        
            payment_content += make_line("        </PmtTpInf>")
            # amount 
            payment_content += make_line("        <Amt>")
            payment_content += make_line("          <InstdAmt Ccy=\"{0}\">{1:.2f}</InstdAmt>".format(
                payment['currency'], payment['amount']))
            payment_content += make_line("        </Amt>")
            # creditor account
            # creditor account identification
            if payment['transaction_type'] == "ESR":
                # add creditor information
                payment_content += make_line("        <Cdtr>") 
                payment_content += make_line("          <Nm>{0}</Nm>".format(payment['receiver_name']))
                payment_content += make_line("          <PstlAdr>")
                payment_content += make_line("            <StrtNm>{0}</StrtNm>".format(payment['receiver_street']))
                payment_content += make_line("            <BldgNb>{0}</BldgNb>".format(payment['receiver_building']))
                payment_content += make_line("            <PstCd>{0}</PstCd>".format(payment['receiver_pincode']))
                payment_content += make_line("            <TwnNm>{0}</TwnNm>".format(payment['receiver_city']))
                payment_content += make_line("            <Ctry>{0}</Ctry>".format(payment['receiver_country']))
                payment_content += make_line("          </PstlAdr>")
                payment_content += make_line("        </Cdtr>") 
                # ESR payment
                payment_content += make_line("        <CdtrAcct>")
                payment_content += make_line("          <Id>")
                payment_content += make_line("            <Othr>")
                # ESR participant number
                if payment['esr_participant_no']:
                    payment_content += make_line("              <Id>{0}</Id>".format(payment['esr_participant_no']))
                else:
                    # no particpiation number: not valid record, skip
                    content += add_invalid_remark( _("{0}: no ESR participation number found").format(payment['name']) )
                    skipped.append(payment['name'])
                    continue
                payment_content += make_line("            </Othr>")
                payment_content += make_line("          </Id>")
                payment_content += make_line("        </CdtrAcct>")
                # Remittance Information
                payment_content += make_line("        <RmtInf>")
                payment_content += make_line("          <Strd>")
                # Creditor Reference Information
                payment_content += make_line("            <CdtrRefInf>")
                # ESR reference 
                if payment['esr_reference']:
                    payment_content += make_line("              <Ref>{0}</Ref>".format(payment['esr_reference']))
                else:
                    # no ESR reference: not valid record, skip
                    content += add_invalid_remark( _("{0}: no ESR reference found").format(payment['name']) )
                    skipped.append(payment['name'])
                    continue    
                payment_content += make_line("            </CdtrRefInf>")
                payment_content += make_line("          </Strd>")
                payment_content += make_line("        </RmtInf>")
            else:
                # IBAN or SEPA payment
                # add creditor information
                payment_content += make_line("        <Cdtr>") 
                payment_content += make_line("          <Nm>{0}</Nm>".format(payment['receiver_name']))
                payment_content += make_line("          <PstlAdr>")
                payment_content += make_line("            <StrtNm>{0}</StrtNm>".format(payment['receiver_street']))
                payment_content += make_line("            <BldgNb>{0}</BldgNb>".format(payment['receiver_building']))
                payment_content += make_line("            <PstCd>{0}</PstCd>".format(payment['receiver_pincode']))
                payment_content += make_line("            <TwnNm>{0}</TwnNm>".format(payment['receiver_city']))
                payment_content += make_line("            <Ctry>{0}</Ctry>".format(payment['receiver_country']))
                payment_content += make_line("          </PstlAdr>")
                payment_content += make_line("        </Cdtr>") 
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
                if payment['receiver_iban']:
                    payment_content += make_line("            <IBAN>{0}</IBAN>".format( 
                        payment['receiver_iban'].replace(" ", "") ))
                else:
                    # no iban: not valid record, skip
                    content += add_invalid_remark( _("{0}: no IBAN found").format(payment['name']) )
                    skipped.append(payment['name'])
                    continue
                payment_content += make_line("          </Id>")
                payment_content += make_line("        </CdtrAcct>")
                                        
            # close payment record
            payment_content += make_line("      </CdtTrfTxInf>")
            payment_content += make_line("    </PmtInf>")
            # once the payment is extracted for payment, submit the record
            transaction_count += 1
            control_sum += payment['amount']
            content += payment_content
        # add footer
        content += make_line("  </CstmrCdtTrfInitn>")
        content += make_line("</Document>")
        # insert control numbers
        content = content.replace(transaction_count_identifier, "{0}".format(transaction_count))
        content = content.replace(control_sum_identifier, "{:.2f}".format(control_sum))
        
        return { 'content': content, 'skipped': skipped }
    #except IndexError:
    #    frappe.msgprint( _("Please select at least one payment."), _("Information") )
    #    return
    #except:
    #    frappe.throw( _("Error while generating xml. Make sure that you made required customisations to the DocTypes.") )
    #    return
