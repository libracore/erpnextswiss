# -*- coding: utf-8 -*-
# Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#
# This is an xml content wrapper for ERPNext Sales Invoice and Purchase Invoice to ZUGFeRD XML
#
#
import frappe
from erpnextswiss.erpnextswiss.common_functions import get_primary_address
from frappe import _
from bs4 import BeautifulSoup
from datetime import datetime
from facturx import check_facturx_xsd
from erpnextswiss.erpnextswiss.zugferd.codelist import get_unit_code
import html          # used to escape xml content

"""
Creates an XML file from a sales invoice
:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_xml(sales_invoice, verify=True):
    try:
        # get original document
        sinv = frappe.get_doc("Sales Invoice", sales_invoice)
        company = frappe.get_doc("Company", sinv.company)
        # compile notes
        notes = []
        if sinv.terms:
            notes.append({
                'text': html.escape(BeautifulSoup(sinv.terms, "lxml").text or "")
            })
        if hasattr(sinv, 'eingangstext') and sinv.eingangstext:
            notes.append({
                'text': html.escape(BeautifulSoup(sinv.eingangstext, "lxml").text or "")
            })
        if len(notes) == 0:
            notes.append({
                'text': html.escape("Sales Invoice {title} ({number}), {date}".format(
                    title=sinv.title, number=sinv.name, date=sinv.posting_date))
            })
        # compile xml content
        data = {
            'name': html.escape(sinv.name),
            'issue_date': "{year:04d}{month:02d}{day:02d}".format(
              year=sinv.posting_date.year, month=sinv.posting_date.month, day=sinv.posting_date.day),
            'notes': notes,
            'company': html.escape(sinv.company),
            'tax_id': html.escape(company.tax_id or ""),
            'customer': html.escape(sinv.customer),
            'customer_name': html.escape(sinv.customer_name),
            'currency': sinv.currency,
            'payment_terms': html.escape(sinv.payment_terms_template or ""),
            'due_date': "{year:04d}{month:02d}{day:02d}".format(
              year=sinv.due_date.year, month=sinv.due_date.month, day=sinv.due_date.day),
            'total': sinv.total,
            'discount': (sinv.total - sinv.net_total),
            'net_total': sinv.net_total,
            'total_tax': sinv.total_taxes_and_charges,
            'grand_total': (sinv.rounded_total or sinv.grand_total),
            'prepaid_amount': ((sinv.rounded_total or sinv.grand_total) - sinv.outstanding_amount),
            'outstanding_amount': sinv.outstanding_amount,
            'po_no': sinv.po_no
        }
        data['items'] = []
        for item in sinv.items:
            item_data = {
                'idx': item.idx,
                'item_code': html.escape(item.item_code),
                'item_name': html.escape(item.item_name),
                'barcode': item.barcode,
                'price_list_rate': item.price_list_rate,
                'rate': item.rate,
                'unit_code': get_unit_code(item.uom),
                'qty': item.qty,
                'amount': item.amount
            }
            data['items'].append(item_data)


        if sinv.taxes and sinv.taxes[0].rate:
            data['overall_tax_rate_percent'] = sinv.taxes[0].rate
            data['taxes'] = []
            for tax in sinv.taxes:
                tax_data = {
                    'tax_amount': tax.tax_amount,
                    'net_amount': (tax.total - tax.tax_amount),
                    'rate': tax.rate
                }
                data['taxes'].append(tax_data)
        else:
            data['overall_tax_rate_percent'] = 0
        
        company_address = get_primary_address(target_name=sinv.company, target_type="Company")
        if company_address:
            data['company_address'] = {
                'address_line1': html.escape(company_address.address_line1 or ""),
                'address_line2': html.escape(company_address.address_line2 or ""),
                'pincode': html.escape(company_address.pincode or ""),
                'city': html.escape(company_address.city or ""),
                'country_code': company_address['country_code'] or "CH"
            }
        else:
            data['company_address'] = {
                'address_line1': "",
                'address_line2': "",
                'pincode': "",
                'city': "",
                'country_code': "CH"
            }            
        customer_address = frappe.get_doc("Address", sinv.customer_address)
        if customer_address:
            customer_country_code = frappe.get_value("Country", customer_address.country, "code").upper()
            data['customer_address'] = {
                'address_line1': html.escape(customer_address.address_line1 or ""),
                'address_line2': html.escape(customer_address.address_line2 or ""),
                'pincode': html.escape(customer_address.pincode or ""),
                'city': html.escape(customer_address.city or ""),
                'country_code': customer_country_code or "CH"
            }
        else:
            data['customer_address'] = {
                'address_line1': "",
                'address_line2': "",
                'pincode': "",
                'city': "",
                'country_code': "CH"
            }            

        xml = frappe.render_template('erpnextswiss/erpnextswiss/zugferd/en16931.html', data)
        
        # verify the generated xml
        if verify:
            try:
                if not check_facturx_xsd(facturx_xml=xml.encode('utf-8')):
                    frappe.log_error( _("XML validation failed for {0}").format(sales_invoice), "ZUGFeRD")
                    return None
            except Exception as err:
                frappe.log_error("XML validation error ({2}): {0}\n{1}".format(err, xml, sales_invoice), "ZUGFeRD XSD validation")
        return xml
    except Exception as err:
        frappe.log_error("Failure during XML generation for {1}: {0}".format(err, sales_invoice), "ZUGFeRD")
        return None
