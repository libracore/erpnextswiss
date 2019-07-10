# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#
# This is an xml content wrapper for ERPNext Sales Invoice and Purchase Invoice to ZUGFeRD XML
#
#
import frappe
from erpnextswiss.erpnextswiss.common_functions import make_line
from frappe import _

"""
Creates an XML file from a sales invoice

:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_xml(sales_invoice):
    try:
        # get original document
        sinv = frappe.get_doc("Sales Invoice", sales_invoice)
        # compile xml content, header
        xml = make_line("<?xml version='1.0' encoding='UTF-8' ?>")
        xml += make_line("<rsm:CrossIndustryInvoice xmlns:a=\"urn:un:unece:uncefact:data:standard:QualifiedDataType:100\" xmlns:rsm=\"urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100\" xmlns:qdt=\"urn:un:unece:uncefact:data:standard:QualifiedDataType:10\" xmlns:ram=\"urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100\" xmlns:xs=\"http://www.w3.org/2001/XMLSchema\" xmlns:udt=\"urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100\">")
        xml += make_line("  <rsm:ExchangedDocumentContext>")
        xml += make_line("    <ram:GuidelineSpecifiedDocumentContextParameter>")
        xml += make_line("      <ram:ID>urn:cen.eu:en16931:2017</ram:ID>")
        xml += make_line("    </ram:GuidelineSpecifiedDocumentContextParameter>")
        xml += make_line("  </rsm:ExchangedDocumentContext>")
        xml += make_line("  <rsm:ExchangedDocument>")
        # document ID
        xml += make_line("    <ram:ID>{id}</ram:ID>".format(id=sinv.name))
        # codes: refer to UN/CEFACT code list
        xml += make_line("    <ram:TypeCode>380</ram:TypeCode>")
        # posting date as "20180305"
        xml += make_line("    <ram:IssueDateTime>")
        xml += make_line("      <udt:DateTimeString format=\"102\">{year}{month}{day}</udt:DateTimeString>".format(year=sinv.posting_date.year, month=sinv.posting_date.month, day=sinv.posting_date.day))
        xml += make_line("    </ram:IssueDateTime>")
        # note to the invoice (e.g. "Rechnung gemäß Bestellung vom 01.03.2018.")
        xml += make_line("    <ram:IncludedNote>")
        xml += make_line("      <ram:Content>{invoice} {title} ({number}), {date}</ram:Content>".format(invoice=_("Sales Invoice"), title=sinv.title, number=sinv.name, date=sinv.posting_date))
        xml += make_line("    </ram:IncludedNote>")
        # details of the invoice issuing company
        xml += make_line("    <ram:IncludedNote>")
        company = frappe.get_doc("Company", sinv.company)
        company_address_links = frappe.get_all('Dynamic Link', filters={'link_doctype': 'Company', 'link_name': sinv.company, 'parenttype': 'Address', 'is_primary_address': 1}, fields='parent')
        if not company_address_links:
            # try secondary address
                company_address_links = frappe.get_all('Dynamic Link', filters={'link_doctype': 'Company', 'link_name': sinv.company, 'parenttype': 'Address'}, fields='parent')
        address = frappe.get_doc("Address", company_address_links[0]['parent'])
        country = frappe.get_doc("Country", address.country)
        xml += make_line("      <ram:Content>{company}\r\n{address}\r\nGeschäftsführer: {ceo}\r\nHandelsregisternummer: {tax_id}</ram:Content>".format(
            company=sinv.company, address="{adr}, {plz}, {city}".format(adr=address.address_line1, plz=address.pincode, city=address.city), ceo="-", tax_id=company.tax_id))
        # subject code: see UNCL 4451
        xml += make_line("      <ram:SubjectCode>REG</ram:SubjectCode>")
        xml += make_line("    </ram:IncludedNote>")
        xml += make_line("  </rsm:ExchangedDocument>")
        xml += make_line("  <rsm:SupplyChainTradeTransaction>")
        # add line items
        for item in sinv.items:
            xml += make_line("    <ram:IncludedSupplyChainTradeLineItem>")
            xml += make_line("      <ram:AssociatedDocumentLineDocument>")
            xml += make_line("        <ram:LineID>{idx}</ram:LineID>".format(idx=loop.index))
            xml += make_line("      </ram:AssociatedDocumentLineDocument>")
            xml += make_line("      <ram:SpecifiedTradeProduct>")
            #xml += make_line("        <ram:GlobalID schemeID=\"0160\">4012345001235</ram:GlobalID>")
            xml += make_line("        <ram:SellerAssignedID>{item_code}</ram:SellerAssignedID>".format(item_code=item.item_code))
            xml += make_line("        <ram:Name>{item_name}</ram:Name>".format(item.item_name))
            xml += make_line("      </ram:SpecifiedTradeProduct>")
            xml += make_line("      <ram:SpecifiedLineTradeAgreement>")
            # gross price: price list
            xml += make_line("        <ram:GrossPriceProductTradePrice>")
            xml += make_line("          <ram:ChargeAmount>{rate:.2f}</ram:ChargeAmount>".format(rate=item.pricelist_rate))
            xml += make_line("        </ram:GrossPriceProductTradePrice>")
            # net price: rate
            xml += make_line("        <ram:NetPriceProductTradePrice>")
            xml += make_line("          <ram:ChargeAmount>{rate:.2f}</ram:ChargeAmount>".format(rate=item.rate))
            xml += make_line("        </ram:NetPriceProductTradePrice>")
            xml += make_line("      </ram:SpecifiedLineTradeAgreement>")
            # quantity: unit see UNCL 6411
            xml += make_line("      <ram:SpecifiedLineTradeDelivery>")
            xml += make_line("        <ram:BilledQuantity unitCode=\"{unit}\">{qty}</ram:BilledQuantity>".format(unit="C62", qty=item.qty))
            xml += make_line("      </ram:SpecifiedLineTradeDelivery>")
            xml += make_line("      <ram:SpecifiedLineTradeSettlement>")
            # tax per item
            gross_item_amount = item.amount
            for tax in item.taxes:
                gross_item_amount = gross_item_amount * ((100 + tax.rate) / 100)
            overall_tax_rate_percent = 100 * (gross_item_amount / item_amount)
            xml += make_line("        <ram:ApplicableTradeTax>")
            xml += make_line("          <ram:TypeCode>VAT</ram:TypeCode>")
            xml += make_line("          <ram:CategoryCode>S</ram:CategoryCode>")
            xml += make_line("          <ram:RateApplicablePercent>{percent:.2f}</ram:RateApplicablePercent>".format(percent=overall_tax_rate_percent))
            xml += make_line("        </ram:ApplicableTradeTax>")
            # line total in gross (including tax)
            xml += make_line("        <ram:SpecifiedTradeSettlementLineMonetarySummation>")
            xml += make_line("          <ram:LineTotalAmount>{gross_amount:.2f}</ram:LineTotalAmount>".format(gross_amount=gross_item_amount))
            xml += make_line("        </ram:SpecifiedTradeSettlementLineMonetarySummation>")
            xml += make_line("      </ram:SpecifiedLineTradeSettlement>")
            xml += make_line("    </ram:IncludedSupplyChainTradeLineItem>")
        # seller details
        xml += make_line("    <ram:ApplicableHeaderTradeAgreement>")
        xml += make_line("      <ram:SellerTradeParty>")
        #xml += make_line("        <ram:GlobalID schemeID=\"0088\">4000001123452</ram:GlobalID>")
        xml += make_line("        <ram:Name>{company}</ram:Name>".format(company=sinv.company))
        xml += make_line("        <ram:PostalTradeAddress>")
        xml += make_line("          <ram:PostcodeCode>{plz}</ram:PostcodeCode>".format(plz=address.pincode))
        xml += make_line("          <ram:LineOne>{adr}</ram:LineOne>".format(adr=address.address_line1))
        xml += make_line("          <ram:CityName>{city}</ram:CityName>".format(city=address.city))
        xml += make_line("          <ram:CountryID>{country}</ram:CountryID>".format(country=country.code.upper()))
        xml += make_line("        </ram:PostalTradeAddress>")
        # tax registration
        #xml += make_line("        <ram:SpecifiedTaxRegistration>")
        #xml += make_line("          <ram:ID schemeID=\"FC\">201/113/40209</ram:ID>")
        #xml += make_line("        </ram:SpecifiedTaxRegistration>")
        xml += make_line("        <ram:SpecifiedTaxRegistration>")
        xml += make_line("          <ram:ID schemeID=\"VA\">{tax_id}</ram:ID>".format(tax_id=company.tax_id))
        xml += make_line("        </ram:SpecifiedTaxRegistration>")
        xml += make_line("      </ram:SellerTradeParty>")
        # customer/buyer details
        xml += make_line("      <ram:BuyerTradeParty>")
        xml += make_line("        <ram:ID>{customer}</ram:ID>".format(sinv.customer))
        #xml += make_line("        <ram:GlobalID schemeID=\"0088\">4000001987658</ram:GlobalID>")
        xml += make_line("        <ram:Name>{customer_name</ram:Name>".format(customer_name=sinv.customer_name))
        customer_address = frappe.get_doc("Address", sinv.customer_address)
        customer_country = frappe.get_doc("Country", customer_address.country)
        xml += make_line("        <ram:PostalTradeAddress>")
        xml += make_line("          <ram:PostcodeCode>{plz}</ram:PostcodeCode>".format(plz=customer_address.pincode))
        xml += make_line("          <ram:LineOne>{adr}</ram:LineOne>".format(adr=customer_address.address_line1))
        xml += make_line("          <ram:CityName>{city}</ram:CityName>".format(city=customer_address.city))
        xml += make_line("          <ram:CountryID>{country}</ram:CountryID>".format(country=customer_country.code.upper()))
        xml += make_line("        </ram:PostalTradeAddress>")
        xml += make_line("      </ram:BuyerTradeParty>")
        xml += make_line("    </ram:ApplicableHeaderTradeAgreement>")
        # related delivery
        #xml += make_line("    <ram:ApplicableHeaderTradeDelivery>")
        #xml += make_line("      <ram:ActualDeliverySupplyChainEvent>")
        #xml += make_line("        <ram:OccurrenceDateTime>")
        #xml += make_line("          <udt:DateTimeString format=\"102\">20180305</udt:DateTimeString>")
        #xml += make_line("        </ram:OccurrenceDateTime>")
        #xml += make_line("      </ram:ActualDeliverySupplyChainEvent>")
        #xml += make_line("    </ram:ApplicableHeaderTradeDelivery>")
        # payment details
        xml += make_line("    <ram:ApplicableHeaderTradeSettlement>")
        xml += make_line("      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>")
        xml += make_line("      <ram:ApplicableTradeTax>")
        xml += make_line("        <ram:CalculatedAmount>19.25</ram:CalculatedAmount>")
        xml += make_line("        <ram:TypeCode>VAT</ram:TypeCode>")
        xml += make_line("        <ram:BasisAmount>275.00</ram:BasisAmount>")
        xml += make_line("        <ram:CategoryCode>S</ram:CategoryCode>")
        xml += make_line("        <ram:RateApplicablePercent>7.00</ram:RateApplicablePercent>")
        xml += make_line("      </ram:ApplicableTradeTax>")
        xml += make_line("      <ram:ApplicableTradeTax>")
        xml += make_line("        <ram:CalculatedAmount>37.62</ram:CalculatedAmount>")
        xml += make_line("        <ram:TypeCode>VAT</ram:TypeCode>")
        xml += make_line("        <ram:BasisAmount>198.00</ram:BasisAmount>")
        xml += make_line("        <ram:CategoryCode>S</ram:CategoryCode>")
        xml += make_line("        <ram:RateApplicablePercent>19.00</ram:RateApplicablePercent>")
        xml += make_line("      </ram:ApplicableTradeTax>")
        xml += make_line("      <ram:SpecifiedTradePaymentTerms>")
        xml += make_line("        <ram:Description>Zahlbar innerhalb 30 Tagen netto bis 04.04.2018, 3% Skonto innerhalb 10 Tagen bis 15.03.2018</ram:Description>")
        xml += make_line("      </ram:SpecifiedTradePaymentTerms>")
        xml += make_line("      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>")
        xml += make_line("        <ram:LineTotalAmount>473.00</ram:LineTotalAmount>")
        xml += make_line("        <ram:ChargeTotalAmount>0.00</ram:ChargeTotalAmount>")
        xml += make_line("        <ram:AllowanceTotalAmount>0.00</ram:AllowanceTotalAmount>")
        xml += make_line("        <ram:TaxBasisTotalAmount>473.00</ram:TaxBasisTotalAmount>")
        xml += make_line("		<ram:TaxTotalAmount currencyID=\"EUR\">56.87</ram:TaxTotalAmount>")
        xml += make_line("        <ram:GrandTotalAmount>529.87</ram:GrandTotalAmount>")
        xml += make_line("        <ram:TotalPrepaidAmount>0.00</ram:TotalPrepaidAmount>")
        xml += make_line("        <ram:DuePayableAmount>529.87</ram:DuePayableAmount>")
        xml += make_line("      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>")
        xml += make_line("    </ram:ApplicableHeaderTradeSettlement>")
        xml += make_line("  </rsm:SupplyChainTradeTransaction>")
        xml += make_line("</rsm:CrossIndustryInvoice>")
        
        return xml
    except Exception as err:
        return "Unable to open sales invoice: {0}".format(err)

"""
Extracts the relevant content for a purchase invoice from a ZUGFeRD XML

:params:zugferd_xml:    xml content (string)
:return:                simplified dict with content
"""
def get_content_from_zugferd(zugferd_xml):
    
