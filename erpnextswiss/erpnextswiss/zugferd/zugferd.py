# -*- coding: utf-8 -*-
# Copyright (c) 2018-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
#


import frappe
from frappe.utils.pdf import get_pdf
from frappe.utils import flt, cint
from erpnextswiss.erpnextswiss.zugferd.zugferd_xml import create_zugferd_xml
from facturx import generate_from_binary, get_facturx_xml_from_pdf, generate_facturx_from_file
try:            # factur-x v3.0 onwards
    from facturx import xml_check_xsd
except:         # factur-x before v3.0 
    from facturx import check_facturx_xsd as xml_check_xsd
from datetime import datetime, date
from bs4 import BeautifulSoup
from frappe import _

"""
Creates an XML file from a sales invoice
:params:sales_invoice:   document name of the sale invoice
:returns:                xml content (string)
"""
def create_zugferd_pdf(docname, verify=True, format=None, doc=None, doctype="Sales Invoice", no_letterhead=0):
    xml = None
    try:
        html = frappe.get_print(doctype, docname, format, doc=doc, no_letterhead=no_letterhead)
        try:
            pdf = get_pdf(html, print_format=format)
        except:
            # this is a fallback to Frappe ERPNext that does not support dynamic print format options (such as smart shrinking)
            pdf = get_pdf(html)
            
        xml = create_zugferd_xml(docname)
        
        if xml: 
            facturx_pdf = generate_from_binary(pdf, xml.encode('utf-8'))  ## Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
            return facturx_pdf
        else:
            # failed to generate xml, fallback
            return get_pdf(html)
    except Exception as err:
        frappe.log_error("Unable to create zugferdPDF for {2}: {0}\n{1}".format(err, xml, docname), "ZUGFeRD")
        # fallback to normal pdf
        return get_pdf(html)

@frappe.whitelist()
def download_zugferd_pdf(sales_invoice_name, format=None, doc=None, no_letterhead=0, verify=True):
    frappe.local.response.filename = "{name}.pdf".format(name=sales_invoice_name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = create_zugferd_pdf(sales_invoice_name, verify=verify, format=format, doc=doc, no_letterhead=no_letterhead)
    frappe.local.response.type = "download"
    return

@frappe.whitelist()
def download_zugferd_xml(sales_invoice_name):
    frappe.local.response.filename = "{name}.xml".format(name=sales_invoice_name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = create_zugferd_xml(sales_invoice_name)
    frappe.local.response.type = "download"
    return
    
@frappe.whitelist()    
def get_xml(path):
    with open(path, "rb") as file:
        pdf = file.read()
    
    try:
        xml_filename, xml_content = get_facturx_xml_from_pdf(pdf)
    except Exception as err:
        # only report error log in debug mode (zugferd wizard and batch processing use this as first cascade, so failing to read zugferd because a file does not have an xml part is not necessarily an error)
        if cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "debug_mode")):
            frappe.log_error("{0}<br>{1}".format(path, err), _("Reading zugferd xml failed") )
        xml_content = None
        
    return xml_content

"""
Extracts the relevant content for a purchase invoice from a ZUGFeRD XML
:params:zugferd_xml:    xml content (string)
:return:                simplified dict with content
"""
def get_content_from_zugferd(zugferd_xml, debug=False):
    soup = BeautifulSoup(zugferd_xml, 'lxml')
    # dict for invoice
    invoice = {'source': 'ZUGFeRD'}
  
    # seller information
    seller = soup.find('ram:sellertradeparty')
    invoice['supplier_name'] = seller.find('ram:name').string
    invoice['supplier_taxid'] = seller.find('ram:id').string
    invoice['supplier_globalid'] = seller.find('ram:id').string
    invoice['supplier_pincode'] = seller.find('ram:postcodecode').string if seller.find('ram:postcodecode') else  ""
    invoice['supplier_al'] = seller.find('ram:lineone').string if seller.find('ram:lineone') else ""
    invoice['supplier_city'] = seller.find('ram:cityname').string if seller.find('ram:cityname') else ""
    invoice['supplier_country'] = seller.find('ram:countryid').string if seller.find('ram:countryid') else frappe.defaults.get_global_default("country")
    
    supplier_match_by_tax_id = frappe.get_all("Supplier", 
                                filters={'tax_id': invoice['supplier_taxid']},
                                fields=['name'])
    if len(supplier_match_by_tax_id) > 0:
        # matched by tax id
        invoice['supplier'] = supplier_match_by_tax_id[0]['name']
    else:
        supplier_match_by_name = frappe.get_all("Supplier", 
                                    filters={'supplier_name': invoice['supplier_name']},
                                    fields=['name'])   
        if len(supplier_match_by_name) > 0:
            # matched by supplier name
            invoice['supplier'] = supplier_match_by_name[0]['name']  
        else:
            # need to insert new supplier
            invoice['supplier'] = None
    
    # find invoice date
    try:        
        date_str = soup.find('ram:issuedatetime').find('udt:datetimestring').string
        invoice['posting_date'] = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except:
        # use default as due date
        today = date.today()
        invoice['posting_date'] = today.strftime("%Y-%m-%d")
        
    # find due date
    try:        
        date_str = soup.find('ram:duedatedatetime').find('udt:datetimestring').string
        invoice['due_date'] = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except:
        # use default as due date
        today = date.today()
        invoice['due_date'] = today.strftime("%Y-%m-%d")

    document_context = soup.find('rsm:exchangeddocument')
    if document_context.find('ram:content'):
        invoice['terms'] = document_context.find('ram:content').string
    else:
        invoice['terms'] = None         # if no content is provided, set to None
    
    doc_id = document_context.find('ram:id').string
    invoice['doc_id'] = doc_id
    
    specified_payment_terms = soup.find('ram:specifiedtradepaymentterms') 
    #if specified_payment_terms:
        #description =  specified_payment_terms.find('ram:description').string or ""
        #invoice['payment_terms_description'] = description
  
    invoice['currency'] = soup.find('ram:invoicecurrencycode').string
    
    applicable_tax = soup.find('ram:applicabletradetax')
    tax_rate = applicable_tax.find('ram:rateapplicablepercent').string
    invoice['tax_rate'] = tax_rate
    # find tax template matching the rate
    tax_template_match = frappe.get_all("Purchase Taxes and Charges",
                                        filters={'rate': tax_rate},
                                        fields=['parent'])
    if len(tax_template_match) > 0:
        invoice['tax_template'] = tax_template_match[0]['parent']
    else:
        invoice['tax_template'] = None

    # collect items
    items = []
    for item in soup.find_all('ram:includedsupplychaintradelineitem'):
        _item = {
            'net_price': item.find('ram:netpriceproducttradeprice').find('ram:chargeamount').string, # if item.find('ram:netpriceproducttradeprice') else 0,
            'qty': flt(item.find('ram:billedquantity').string) if item.find('ram:billedquantity') else 0,
            'seller_item_code': item.find('ram:sellerassignedid').string,
            'item_name': item.find('ram:name').string,
            'item_code': None
        }
        if _item['qty'] == 0:       # skip 0-qty positions
            continue
            
        # match by seller item code
        match_item_by_code = frappe.get_all("Item",
                                            filters={'item_code': _item['seller_item_code']},
                                            fields=['name'])
        if len(match_item_by_code) > 0: 
            _item['item_code'] = match_item_by_code[0]['name']
        else:
            # match by supplier item code
            supplier_item_matches = frappe.db.sql("""
                SELECT `parent`
                FROM `tabItem Supplier`
                WHERE 
                    `supplier` = "{supplier}"
                    AND `supplier_part_no` = "{supplier_item}"
                ;""".format(supplier=invoice['supplier'], supplier_item=_item['seller_item_code']), as_dict=True)
            if len(supplier_item_matches) > 0:
                _item['item_code'] = supplier_item_matches[0]['parent']
            else:
                # match by item name
                match_item_by_name = frappe.get_all("Item",
                                                    filters={'item_name': _item['item_name']},
                                                    fields=['name'])
                if len(match_item_by_name) > 0: 
                    _item['item_code'] = match_item_by_name[0]['name']    

        #add item
        items.append(_item)
        
    invoice['items'] = items
    
    total_amounts = soup.find('ram:specifiedtradesettlementheadermonetarysummation')

    invoice['line_total'] = total_amounts.find('ram:linetotalamount').string
    invoice['total_taxes'] = total_amounts.find('ram:taxtotalamount').string
    invoice['grand_total'] = total_amounts.find('ram:grandtotalamount').string
    
    return invoice
