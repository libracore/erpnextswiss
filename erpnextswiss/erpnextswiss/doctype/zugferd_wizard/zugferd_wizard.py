# -*- coding: utf-8 -*-
# Copyright (c) 2019-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import os
from erpnextswiss.erpnextswiss.zugferd.zugferd import get_xml, get_content_from_zugferd



    
     
    

class ZUGFeRDWizard(Document):
	
    def read_file(self):
        file_path = os.path.join(frappe.utils.get_bench_path(), 'sites', frappe.utils.get_site_path()) + self.file
        xml_content = get_xml(file_path)
        invoice = get_content_from_zugferd(xml_content)
        # render html
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/zugferd_wizard/zugferd_content.html', invoice)
        # return html and dict
        return { 'html': content, 'dict': invoice }
	 
    def hello(self):
        file_path = os.path.join(frappe.utils.get_bench_path(), 'sites', frappe.utils.get_site_path()) + self.file
        xml_content = get_xml(file_path)
        invoice = get_content_from_zugferd(xml_content)
        frappe.msgprint("hey")
        
        #generate supplier
        frappe.msgprint(invoice['supplier_identifikation'])
        if  invoice['supplier_identifikation'] == "0":
            doc = frappe.get_doc({
                'doctype': 'Supplier',
                'title': invoice['supplier_name'],
                'supplier_name': invoice['supplier_name'],
                'tax_id': invoice['supplier_taxid'],
                'global_id': invoice['supplier_globalid'],
                'supplier_group': "All Supplier Groups" #supplier_group
                })
            doc.insert()
            #generate supplier address
         
            address_doc = frappe.get_doc({
                'doctype': 'Address',
                'address_title': invoice['supplier_name'] + " address",
                'pincode': invoice['supplier_pincode'],
                'address_line1': invoice['supplier_al'],
                'city': invoice['supplier_city'],
                'links': [ {'link_doctype': 'Supplier', 'link_name': invoice['supplier_name']} ]
                #'country': "Schweiz" #seller.find('ram:CountryID').string or ""
            })
            address_doc.insert()
        
       
        
        frappe.msgprint("item" + invoice['item_identifikation'])
        if  invoice['item_identifikation'] == "0":
            item_doc = frappe.get_doc ({
                'item_code': invoice['items']['seller_item_code'],
                'item_name': invoice['items']['item_name']
            })
            item_doc.insert()
        
        
        
        
        pinv_doc = frappe.get_doc({
            'doctype': 'Purchase Invoice',
            'supplier': invoice['supplier_name'],
            'title': invoice['supplier_name'],
            'due_date': invoice['due_date'],
            'currency': invoice['currency'],
            #'payment_schedule[0].payment_term': invoice['payment_terms'],
            'terms': invoice['terms'],
            'naming_series': 'PINV-',
            'status': 'Draft',
            #'taxes_and_charges': invoice['tax_rule'],
    
            'items': [{
                'item_code': 'Odile Low-UBL-420',
                'item_name': 'Odile Low Ultra Blue',
                'qty': 12,
                'conversion_factor': 1,
                'rate': 12,
            }],
        })
        
    
            
            
        frappe.msgprint("Import successfully")
        
   
        '''
    def read_file(self):
        file_path = os.path.join(frappe.utils.get_bench_path(), 'sites', frappe.utils.get_site_path()) + self.file
        xml_content = get_xml(file_path)
        invoice = get_content_from_zugferd(xml_content)
        # render html
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/zugferd_wizard/zugferd_content.html', invoice)
        # return html and dict
        return { 'html': content, 'dict': invoice }
        
        '''
        
        
    @frappe.whitelist()  
    def hello2():
        frappe.msgprint(invoice)
    
         
        
        
    
    
    def hinz(self):
        file_path = os.path.join(frappe.utils.get_bench_path(), 'sites', frappe.utils.get_site_path()) + self.file
        xml_content = get_xml(file_path)
        invoice = get_content_from_zugferd(xml_content)
    
    @frappe.whitelist()
    def create_supplier(invoice):
        doc = frappe.get_doc({
            'doctype': 'Supplier',
            'title': seller.find('ram:name').string,
            'supplier_name': seller.find('ram:name').string,
            'tax_id': seller.find('ram:id').string,
            'supplier_group': "All Supplier Groups" #supplier_group
        })
        doc.insert()
    
        frappe.msgprint("<b>" + "Added new supplier: " + "</b>" + "<br>" + "<br>" + "<b>" + "Title: " + "</b>" 
        + doc.title + "<br>" + "<b>" + "Supplier Name: " "</b>" + doc.supplier_name + "<br>" + "<b>" + "Global ID: " 
        + "</b>" + doc.global_id + "<br>" + "<b>" + "Supplier Group: " + "</b>" + doc.supplier_group + "<br>")
    
        #INSERTION
        address_doc = frappe.get_doc({
            'doctype': 'Address',
            'address_title': doc.supplier_name + " address",
            'pincode': seller.find('ram:postcodecode').string,
            'address_line1': seller.find('ram:lineone').string,
            'city': 'zürich', #seller.find('ram:cityname').string or "",
            'links': [ {'link_doctype': 'Supplier', 'link_name': doc.supplier_name} ]
            #'country': "Schweiz" #seller.find('ram:CountryID').string or ""
        })
        address_doc.insert()

    def create_purchase_invoice(self):
        pinv_doc = frappe.get_doc({
            'doctype': 'Purchase Invoice',
            'supplier': 'LibraCore',
            'title': invoice['supplier_name'],
            'due_date': invoice['due_date'],
            #'company': 'LibraCore',
            'currency': invoice['currency'],
            'payment_schedule[0].payment_term': invoice['payment_terms'],
            'terms': invoice['terms'],
            'naming_series': 'PINV-',
            'status': 'Draft',
            'taxes_and_charges': invoice['tax_rule'],
            'items': [{
                'item_code': 'Odile Low-UBL-420',
                'item_name': 'Odile Low Ultra Blue',
                'qty': 12,
                'conversion_factor': 1,
                'rate': 12,
            }],
        })
        
    def create_payment_terms(self):
        #INSERTION
        payment_terms = frappe.get_doc({
            'doctype': 'Payment Term',
            'payment_term_name': doc_id + " payment template",
            'invoice_portion': '100.00',
            'credit_days': '30',
            'description': description, 
        })
        payment_terms.insert()
