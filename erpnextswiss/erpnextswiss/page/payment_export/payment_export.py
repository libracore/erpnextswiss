# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore (https://www.libracore.com) and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import time

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
        payments = filter(None, payments)
        
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
                payment_record.company + "</Nm>")
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
                payment_content += make_line("          <BIC>" +
                    payment_account.bic + "</BIC>")
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
    payment_content += make_line("          <Nm>" + 
        payment_record.party + "</Nm>")
    # address of creditor/supplier (should contain at least country and first address line
    # get supplier address
    supplier_address = get_billing_address(payment_record.party)
    if supplier_address == None:
        return None
    payment_content += make_line("          <PstlAdr>")
    # street name
    payment_content += make_line("            <StrtNm>" +
        get_street_name(supplier_address.address_line1) + "</StrtNm>")
    # building number
    payment_content += make_line("            <BldgNb>" +
        get_building_number(supplier_address.address_line1) + "</BldgNb>")
    # postal code
    payment_content += make_line("            <PstCd>{0}</PstCd>".format(
        supplier_address.pincode))
    # town name
    payment_content += make_line("            <TwnNm>" +
        supplier_address.city + "</TwnNm>")
    # country (has to be a two-digit code)
    try:
        country_code = frappe.get_value('Country', supplier_address.country, 'code').upper()
    except:
        frappe.throw( _("Unable to find country code for {0}").format(supplier_address.country))
    if country_code:
        payment_content += make_line("            <Ctry>" +
            country_code + "</Ctry>")
    else:
        # country code not found (not valid)
        return None
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
def get_billing_address(supplier_name):
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

# try to get building number from address line
def get_building_number(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        return parts[-1]
    else:
        return None
# get street name from address line
def get_street_name(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        return "".join(parts[:-1])
    else:
        return address_line
        
