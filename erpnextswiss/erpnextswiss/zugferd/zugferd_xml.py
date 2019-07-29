# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#
# This is an xml content wrapper for ERPNext Sales Invoice and Purchase Invoice to ZUGFeRD XML
#
#
import frappe
from erpnextswiss.erpnextswiss.common_functions import make_line, get_primary_address
from frappe import _
from bs4 import BeautifulSoup
from datetime import datetime
from facturx import check_facturx_xsd

"""
Creates an XML file from a sales invoice

:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_xml(sales_invoice, verify=True):
    try:
        # get original document
        sinv = frappe.get_doc("Sales Invoice", sales_invoice)
        # compile xml content, header
        xml = ("""<?xml version='1.0' encoding='UTF-8' ?>""")
        xml += ("""<rsm:CrossIndustryInvoice xmlns:a="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:10" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">""")
        xml += ("  <rsm:ExchangedDocumentContext>")
        xml += ("    <ram:GuidelineSpecifiedDocumentContextParameter>")
        xml += ("      <ram:ID>urn:cen.eu:en16931:2017</ram:ID>")
        xml += ("    </ram:GuidelineSpecifiedDocumentContextParameter>")
        xml += ("  </rsm:ExchangedDocumentContext>")
        xml += ("  <rsm:ExchangedDocument>")
        # document ID
        xml += ("    <ram:ID>{id}</ram:ID>".format(id=sinv.name))
        # codes: refer to UN/CEFACT code list
        xml += ("    <ram:TypeCode>380</ram:TypeCode>")
        # posting date as "20180305" (Code according to UNCL 2379)
        xml += ("    <ram:IssueDateTime>")
        xml += ("      <udt:DateTimeString format=\"102\">{year:04d}{month:02d}{day:02d}</udt:DateTimeString>".format(year=sinv.posting_date.year, month=sinv.posting_date.month, day=sinv.posting_date.day))
        xml += ("    </ram:IssueDateTime>")
        # note to the invoice (e.g. "Rechnung gemäß Bestellung vom 01.03.2018.")
        xml += ("    <ram:IncludedNote>")
        xml += ("      <ram:Content>{invoice} {title} ({number}), {date}</ram:Content>".format(invoice=_("Sales Invoice"), title=sinv.title, number=sinv.name, date=sinv.posting_date))
        xml += ("    </ram:IncludedNote>")
        # details of the invoice issuing company
        xml += ("    <ram:IncludedNote>")
        company = frappe.get_doc("Company", sinv.company)
        address = get_primary_address(sinv.company)
        if not address:
            frappe.throw( _("Company address not find. Please add a company address for {company}.").format(company=sinv.company))
        country = frappe.get_doc("Country", address.country)
        xml += ("      <ram:Content>{company}\r\n{address}\r\nGeschäftsführer: {ceo}\r\nHandelsregisternummer: {tax_id}</ram:Content>".format(
            company=sinv.company, address="{adr}, {plz}, {city}".format(adr=address.address_line1, plz=address.pincode, city=address.city), ceo="-", tax_id=company.tax_id))
        # subject code: see UNCL 4451
        xml += ("      <ram:SubjectCode>REG</ram:SubjectCode>")
        xml += ("    </ram:IncludedNote>")
        xml += ("  </rsm:ExchangedDocument>")
        xml += ("  <rsm:SupplyChainTradeTransaction>")
        # add line items
        for item in sinv.items:
            xml += ("    <ram:IncludedSupplyChainTradeLineItem>")
            xml += ("      <ram:AssociatedDocumentLineDocument>")
            xml += ("        <ram:LineID>{idx}</ram:LineID>".format(idx=item.idx))
            xml += ("      </ram:AssociatedDocumentLineDocument>")
            xml += ("      <ram:SpecifiedTradeProduct>")
            #xml += ("        <ram:GlobalID schemeID=\"0160\">4012345001235</ram:GlobalID>")
            xml += ("        <ram:SellerAssignedID>{item_code}</ram:SellerAssignedID>".format(item_code=item.item_code))
            xml += ("        <ram:Name>{item_name}</ram:Name>".format(item_name=item.item_name))
            xml += ("      </ram:SpecifiedTradeProduct>")
            xml += ("      <ram:SpecifiedLineTradeAgreement>")
            # gross price: price list
            xml += ("        <ram:GrossPriceProductTradePrice>")
            xml += ("          <ram:ChargeAmount>{rate:.2f}</ram:ChargeAmount>".format(rate=item.price_list_rate))
            xml += ("        </ram:GrossPriceProductTradePrice>")
            # net price: rate
            xml += ("        <ram:NetPriceProductTradePrice>")
            xml += ("          <ram:ChargeAmount>{rate:.2f}</ram:ChargeAmount>".format(rate=item.rate))
            xml += ("        </ram:NetPriceProductTradePrice>")
            xml += ("      </ram:SpecifiedLineTradeAgreement>")
            # quantity: unit see UNCL 6411
            xml += ("      <ram:SpecifiedLineTradeDelivery>")
            xml += ("        <ram:BilledQuantity unitCode=\"{unit}\">{qty}</ram:BilledQuantity>".format(unit="C62", qty=item.qty))
            xml += ("      </ram:SpecifiedLineTradeDelivery>")
            xml += ("      <ram:SpecifiedLineTradeSettlement>")
            # tax per item
            gross_item_amount = item.amount
            for tax in sinv.taxes:
                gross_item_amount = gross_item_amount * ((100 + tax.rate) / 100)
            overall_tax_rate_percent = 100 * (gross_item_amount / item.amount)
            xml += ("        <ram:ApplicableTradeTax>")
            xml += ("          <ram:TypeCode>VAT</ram:TypeCode>")
            xml += ("          <ram:CategoryCode>S</ram:CategoryCode>")
            xml += ("          <ram:RateApplicablePercent>{percent:.2f}</ram:RateApplicablePercent>".format(percent=overall_tax_rate_percent))
            xml += ("        </ram:ApplicableTradeTax>")
            # line total net amount
            xml += ("        <ram:SpecifiedTradeSettlementLineMonetarySummation>")
            xml += ("          <ram:LineTotalAmount>{amount:.2f}</ram:LineTotalAmount>".format(amount=item.amount))
            xml += ("        </ram:SpecifiedTradeSettlementLineMonetarySummation>")
            xml += ("      </ram:SpecifiedLineTradeSettlement>")
            xml += ("    </ram:IncludedSupplyChainTradeLineItem>")
        # seller details
        xml += ("    <ram:ApplicableHeaderTradeAgreement>")
        xml += ("      <ram:SellerTradeParty>")
        #xml += ("        <ram:GlobalID schemeID=\"0088\">4000001123452</ram:GlobalID>")
        xml += ("        <ram:Name>{company}</ram:Name>".format(company=sinv.company))
        xml += ("        <ram:PostalTradeAddress>")
        xml += ("          <ram:PostcodeCode>{plz}</ram:PostcodeCode>".format(plz=address.pincode))
        xml += ("          <ram:LineOne>{adr}</ram:LineOne>".format(adr=address.address_line1))
        xml += ("          <ram:CityName>{city}</ram:CityName>".format(city=address.city))
        xml += ("          <ram:CountryID>{country}</ram:CountryID>".format(country=country.code.upper()))
        xml += ("        </ram:PostalTradeAddress>")
        # tax registration
        #xml += ("        <ram:SpecifiedTaxRegistration>")
        #xml += ("          <ram:ID schemeID=\"FC\">201/113/40209</ram:ID>")
        #xml += ("        </ram:SpecifiedTaxRegistration>")
        xml += ("        <ram:SpecifiedTaxRegistration>")
        xml += ("          <ram:ID schemeID=\"VA\">{tax_id}</ram:ID>".format(tax_id=company.tax_id))
        xml += ("        </ram:SpecifiedTaxRegistration>")
        xml += ("      </ram:SellerTradeParty>")
        # customer/buyer details
        xml += ("      <ram:BuyerTradeParty>")
        xml += ("        <ram:ID>{customer}</ram:ID>".format(customer=sinv.customer))
        #xml += ("        <ram:GlobalID schemeID=\"0088\">4000001987658</ram:GlobalID>")
        xml += ("        <ram:Name>{customer_name}</ram:Name>".format(customer_name=sinv.customer_name))
        try:
            customer_address = frappe.get_doc("Address", sinv.customer_address)
        except:
            frappe.throw( _("Customer address not found. Please make sure the customer has an address.") )
        customer_country = frappe.get_doc("Country", customer_address.country)
        xml += ("        <ram:PostalTradeAddress>")
        xml += ("          <ram:PostcodeCode>{plz}</ram:PostcodeCode>".format(plz=customer_address.pincode))
        xml += ("          <ram:LineOne>{adr}</ram:LineOne>".format(adr=customer_address.address_line1))
        xml += ("          <ram:CityName>{city}</ram:CityName>".format(city=customer_address.city))
        xml += ("          <ram:CountryID>{country}</ram:CountryID>".format(country=customer_country.code.upper()))
        xml += ("        </ram:PostalTradeAddress>")
        xml += ("      </ram:BuyerTradeParty>")
        xml += ("    </ram:ApplicableHeaderTradeAgreement>")
        # related delivery
        xml += ("    <ram:ApplicableHeaderTradeDelivery>")
        #xml += ("      <ram:ActualDeliverySupplyChainEvent>")
        #xml += ("        <ram:OccurrenceDateTime>")
        #xml += ("          <udt:DateTimeString format=\"102\">20180305</udt:DateTimeString>")
        #xml += ("        </ram:OccurrenceDateTime>")
        #xml += ("      </ram:ActualDeliverySupplyChainEvent>")
        xml += ("    </ram:ApplicableHeaderTradeDelivery>")
        # payment details
        xml += ("    <ram:ApplicableHeaderTradeSettlement>")
        xml += ("      <ram:InvoiceCurrencyCode>{currency}</ram:InvoiceCurrencyCode>".format(currency=sinv.currency))
        if sinv.taxes:
            for tax in sinv.taxes:
                xml += ("      <ram:ApplicableTradeTax>")
                xml += ("        <ram:CalculatedAmount>{tax_amount:.2f}</ram:CalculatedAmount>".format(tax_amount=tax.tax_amount))
                xml += ("        <ram:TypeCode>VAT</ram:TypeCode>")
                xml += ("        <ram:BasisAmount>{net_amount:.2f}</ram:BasisAmount>".format(net_amount=(tax.total - tax.tax_amount)))
                xml += ("        <ram:CategoryCode>S</ram:CategoryCode>")
                xml += ("        <ram:RateApplicablePercent>{rate:.2f}</ram:RateApplicablePercent>".format(rate=tax.rate))
                xml += ("      </ram:ApplicableTradeTax>")
        else:
            xml += ("      <ram:ApplicableTradeTax>") 
            xml += ("        <ram:CalculatedAmount>0</ram:CalculatedAmount>")
            xml += ("        <ram:TypeCode>VAT</ram:TypeCode>")
            xml += ("        <ram:BasisAmount>0</ram:BasisAmount>")
            xml += ("        <ram:CategoryCode>S</ram:CategoryCode>")
            xml += ("        <ram:RateApplicablePercent>0</ram:RateApplicablePercent>")                        
            xml += ("      </ram:ApplicableTradeTax>")
        # payment terms (e.g. Zahlbar innerhalb 30 Tagen netto bis 04.04.2018, 3% Skonto innerhalb 10 Tagen bis 15.03.2018)
        xml += ("      <ram:SpecifiedTradePaymentTerms>")
        xml += ("        <ram:Description>{payment_terms}, {due} {due_date}</ram:Description>".format(
            payment_terms=sinv.payment_terms_template, due=_("Payment Due Date"), due_date=sinv.due_date))
        # comfort: due date, code according to UNCL 2379
        xml += ("        <ram:DueDateDateTime>")
        xml += ("          <udt:DateTimeString format=\"102\">{year:04d}{month:02d}{day:02d}</udt:DateTimeString>".format(year=sinv.due_date.year, month=sinv.due_date.month, day=sinv.due_date.day))
        xml += ("        </ram:DueDateDateTime>")
        xml += ("      </ram:SpecifiedTradePaymentTerms>")
        # totals
        xml += ("      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>")
        # net total (from positions)
        xml += ("        <ram:LineTotalAmount>{total}</ram:LineTotalAmount>".format(total=sinv.total))
        # discount
        xml += ("        <ram:ChargeTotalAmount>{discount}</ram:ChargeTotalAmount>".format(discount=(sinv.total - sinv.net_total)))
        # additional charges (not used)
        xml += ("        <ram:AllowanceTotalAmount>0.00</ram:AllowanceTotalAmount>")
        # net total before taxes
        xml += ("        <ram:TaxBasisTotalAmount>{net_total}</ram:TaxBasisTotalAmount>".format(net_total=sinv.net_total))
        # tax amount
        xml += ("        <ram:TaxTotalAmount currencyID=\"{currency}\">{total_tax}</ram:TaxTotalAmount>".format(
            currency=sinv.currency, total_tax=sinv.total_taxes_and_charges))
        # grand total
        xml += ("        <ram:GrandTotalAmount>{grand_total}</ram:GrandTotalAmount>".format(grand_total=sinv.rounded_total))
        # already paid
        xml += ("        <ram:TotalPrepaidAmount>{prepaid_amount}</ram:TotalPrepaidAmount>".format(prepaid_amount=(sinv.rounded_total - sinv.outstanding_amount)))
        # open amount
        xml += ("        <ram:DuePayableAmount>{outstanding_amount}</ram:DuePayableAmount>".format(outstanding_amount=sinv.outstanding_amount))
        xml += ("      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>")
        xml += ("    </ram:ApplicableHeaderTradeSettlement>")
        xml += ("  </rsm:SupplyChainTradeTransaction>")
        xml += ("</rsm:CrossIndustryInvoice>")
        
        # verify the generated xml
        if verify:
            if not check_facturx_xsd(facturx_xml=xml):
                frappe.throw( _("XML validation failed") )
        return xml
    except Exception as err:
        return "Unable to open sales invoice: {0}".format(err)

"""
Extracts the relevant content for a purchase invoice from a ZUGFeRD XML

:params:zugferd_xml:    xml content (string)
:return:                simplified dict with content
"""
def get_content_from_zugferd(zugferd_xml, debug=False):
    # create soup object
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {}
    # get supplier information (seller)
    invoice['supplier_name'] = soup.sellertradeparty.name.get_text()
    # dates (codes: UNCL 2379: 102=JJJJMMTT, 610=JJJJMM, 616=JJJJWW)
    try:
        invoice['posting_date'] = datetime.strptime(
            soup.issuedatetime.datetimestring.get_text(), "%Y%m%d")
    except Exception as err:
        if debug:
            print("Read posting date failed: {err}".format(err=err))
        pass
    return invoice
