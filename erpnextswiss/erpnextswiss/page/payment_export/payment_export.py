from __future__ import unicode_literals

import frappe
#from email_reply_parser import EmailReplyParser
#from markdown2 import markdown
import time

@frappe.whitelist()
def get_payments():
    payments = frappe.get_list('Payment Entry', filters={'docstatus': 0, 'payment_type': 'Pay'}, fields=['name', 'posting_date', 'paid_amount', 'party', 'paid_from'], order_by='posting_date')
    
    return { 'payments': payments }

@frappe.whitelist()
def generate_payment_file(payments):
    # creates a pain.001 payment file from the selected payments
    
    # create xml header
    content = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    content += "<Document xmlns=\"http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd  pain.001.001.03.ch.02.xsd\">\n"
    content += "  <CstmrCdtTrfInitn>\n"
    # create group header
    content += "      <GrpHdr>\n"
    # message ID
    content += "        <MsgId>MSG-" + time.strftime("%Y%m%d%H%M%S") + "</MsgId>\n"
    # creation date and time ( e.g. 2010-02-15T07:30:00 )
    content += "        <CreDtTm>" + time.strftime("%Y-%m-%dT%H:%M:%S") + "</CreDtTm>\n"
    # number of transactions
    content += "        <NbOfTxs>" + len(payments) + "</NbOfTxs>\n"
    # total amount of all transactions ( e.g. 15850.00 )   
    content += "        <CtrlSum>" + get_total_amount(payments) + "</CtrlSum>\n"
    content += "        <InitgPty>\n"
    # company name ( e.g. MUSTER AG )
    content += "          <Nm>" + get_company_name(payments[0]) + "</Nm>\n"
    content += "        </InitgPty>\n"
    content += "      </GrpHdr>\n"

    for payment in payments:
        # create the payment entries
        content += "    <PmtInf>\n"
        content += "      <PmtInfId>{{ payment_info_id PMTINF-01 }}</PmtInfId>\n"
        content += "      <PmtMtd>{{ payment_method TRF }}</PmtMtd>\n"
        content += "      <BtchBookg>true</BtchBookg>\n"
        content += "      <ReqdExctnDt>2010-02-22</ReqdExctnDt>\n"
        content += "      <Dbtr>\n"
        content += "        <Nm>MUSTER AG</Nm>\n"
        content += "        <PstlAdr>\n"
        content += "          <Ctry>CH</Ctry>\n"
        content += "          <AdrLine>SELDWYLA</AdrLine>\n"
        content += "        </PstlAdr>\n"
        content += "      </Dbtr>\n"
        content += "      <DbtrAcct>\n"
        content += "        <Id>\n"
        content += "          <IBAN>CH5481230000001998736</IBAN>\n"
        content += "        </Id>\n"
        content += "      </DbtrAcct>\n"
        content += "      <DbtrAgt>\n"
        content += "        <FinInstnId>\n"
        content += "          <BIC>RAIFCH22</BIC>\n"
        content += "        </FinInstnId>\n"
        content += "      </DbtrAgt>\n"
        content += "      <CdtTrfTxInf>\n"
        content += "        <PmtId>\n"
        content += "          <InstrId>INSTRID-01-01</InstrId>\n"
        content += "          <EndToEndId>ENDTOENDID-001</EndToEndId>\n"
        content += "        </PmtId>\n"
        content += "        <PmtTpInf>\n"
        content += "          <LclInstrm>\n"
        content += "            <Prtry>CH01</Prtry>\n"
        content += "          </LclInstrm>\n"
        content += "        </PmtTpInf>\n"
        content += "        <Amt>\n"
        content += "          <InstdAmt Ccy=\"CHF\">3949.75</InstdAmt>\n"
        content += "        </Amt>\n"
        content += "        <CdtrAcct>\n"
        content += "          <Id>\n"
        content += "            <Othr>\n"
        content += "              <Id>01-39139-1</Id>\n"
        content += "            </Othr>\n"
        content += "          </Id>\n"
        content += "        </CdtrAcct>\n"
        content += "        <RmtInf>\n"
        content += "          <Strd>\n"
        content += "            <CdtrRefInf>\n"
        content += "              <Ref>210000000003139471430009017</Ref>\n"
        content += "            </CdtrRefInf>\n"
        content += "          </Strd>\n"
        content += "        </RmtInf>\n"
        content += "      </CdtTrfTxInf>\n"
        content += "    </PmtInf>\n"
    # add footer
    content += "  </CstmrCdtTrfInitn>\n"
    content += "</Document>\n"
    
    return { 'content': content }

def get_total_amount(payments):
    # get total amount from all payments
    total_amount = float(0)
    for payment in payments:
        payment_amount = frappe.get_value('Payment Entry', payment, 'paid_amount')
        total_amount += payment_amount
        
    return total_amount

def get_company_name(payment_entry):
    return frappe.get_value('Payment Entry', payment_entry, 'company')
    
