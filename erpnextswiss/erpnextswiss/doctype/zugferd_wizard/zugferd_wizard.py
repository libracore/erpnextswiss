# -*- coding: utf-8 -*-
# Copyright (c) 2019-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import os
from erpnextswiss.erpnextswiss.zugferd.zugferd import get_xml, get_content_from_zugferd
from erpnextswiss.erpnextswiss.zugferd.qr_reader import find_qr_content_from_pdf, get_content_from_qr
from frappe import _
import json
from frappe.utils import cint, flt, get_link_to_form, get_url_to_form

class ZUGFeRDWizard(Document):
    def read_file(self):
        file_path = os.path.join(frappe.utils.get_bench_path(), 'sites', frappe.utils.get_site_path()) + self.file
        # try to fetch data from zugferd
        xml_content = get_xml(file_path)
        invoice = None
        if xml_content:
            invoice = get_content_from_zugferd(xml_content)
        else:
            # zugferd failed, fall back to qr-reader
            qr_content = find_qr_content_from_pdf(file_path)
            if qr_content:
                invoice = get_content_from_qr(qr_content, self.default_tax, self.default_item)
        # render html
        if invoice:
            return self.render_invoice(invoice)
        else:
            return { 'html': "", 'dict': None }
    
    def render_invoice(self, invoice):
        if (type(invoice) == str):
            invoice = json.loads(invoice)
            
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/zugferd_wizard/zugferd_content.html', invoice)
        # return html and dict
        return { 'html': content, 'dict': invoice }
            
    def get_default_item(self):
        return frappe.get_cached_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "scanning_default_item")
        
    def create_invoice(self):
        if not self.content_dict:
            frappe.throw( _("Please start by loading a document."), _("Notification") )
        
        settings = frappe.get_doc("ZUGFeRD Settings", "ZUGFeRD Settings")
        
        invoice = json.loads(self.content_dict)
        
        if  not invoice['supplier']:
            # create new supplier
            _supplier = {
                'doctype': 'Supplier',
                'title': invoice['supplier_name'],
                'supplier_name': invoice['supplier_name'],
                'tax_id': invoice['supplier_taxid'],
                'global_id': invoice['supplier_globalid'],
                'supplier_group': frappe.get_value("Buying Settings", "Buying Settings", "supplier_group") or frappe.get_all("Supplier Group", fields=['name'])[0]['name']
            }
            # apply default values
            for d in settings.defaults:
                if d.dt == "Supplier":
                    _supplier[d.field] = d.value
            supplier_doc = frappe.get_doc(_supplier)
            supplier_doc.insert()
            invoice['supplier'] = supplier_doc.name
            
            # generate supplier address
            _address = {
                'doctype': 'Address',
                'address_title': "{0} - {1}".format(invoice['supplier_name'], invoice['supplier_city']),
                'pincode': invoice['supplier_pincode'],
                'address_line1': invoice['supplier_al'],
                'city': invoice['supplier_city'],
                'links': [
                    {
                        'link_doctype': 'Supplier', 
                        'link_name': invoice['supplier']
                    }
                ],
                'country': invoice['supplier_country']
            }
            # apply default values
            for d in settings.defaults:
                if d.dt == "Address":
                    _address[d.field] = d.value
            address_doc = frappe.get_doc(_address)
            address_doc.insert()
        
        # create purchase invoice
        pinv_doc = frappe.get_doc({
            'doctype': 'Purchase Invoice',
            'company': self.company,
            'supplier': invoice.get('supplier'),
            'due_date': invoice.get('due_date'),
            'currency': invoice.get('currency'),
            'bill_no': invoice.get('doc_id'),
            'bill_date': invoice.get('posting_date'),
            'terms': invoice.get('terms')
        })
        
        if invoice.get('esr_reference'):
            pinv_doc.esr_reference_number = invoice.get('esr_reference')
            pinv_doc.payment_type = "ESR"
            
        # find taxes and charges
        taxes_and_charges_template = frappe.db.sql("""
            SELECT `tabPurchase Taxes and Charges Template`.`name`
            FROM `tabPurchase Taxes and Charges`
            LEFT JOIN `tabPurchase Taxes and Charges Template` ON `tabPurchase Taxes and Charges Template`.`name` = `tabPurchase Taxes and Charges`.`parent`
            WHERE 
                `tabPurchase Taxes and Charges Template`.`company` = "{company}"
                AND `tabPurchase Taxes and Charges`.`rate` = {tax_rate}
            ;""".format(company=self.company, tax_rate=flt(invoice.get('tax_rate'))), as_dict=True)
        if len(taxes_and_charges_template) > 0:
            pinv_doc.taxes_and_charges = taxes_and_charges_template[0]['name']
            taxes_template = frappe.get_doc("Purchase Taxes and Charges Template", taxes_and_charges_template[0]['name'])
            for t in taxes_template.taxes:
                pinv_doc.append("taxes", t)
                
        for item in invoice.get("items"):
            if not item.get('item_code'):
                # get item from seller_item_code
                if not frappe.db.exists("Item", item.get('seller_item_code')):
                    # try to find item by supplier item
                    supplier_item_matches = frappe.db.sql("""
                        SELECT `parent`
                        FROM `tabItem Supplier`
                        WHERE 
                            `supplier` = "{supplier}"
                            AND `supplier_part_no` = "{supplier_item}"
                        ;""".format(supplier=pinv_doc.supplier, supplier_item=item.get('seller_item_code')), as_dict=True)
                    if len(supplier_item_matches) > 0:
                        item['item_code'] = supplier_item_matches[0]['parent']
                    else:
                        # create new item
                        _item = {
                            'doctype': "Item",
                            'item_code': item.get('seller_item_code'),
                            'item_name': item.get('item_name'),
                            'item_group': frappe.get_value("ZUGFeRD Settings", "ZUGFeRD Settings", "item_group")
                        }
                        # apply default values
                        for d in settings.defaults:
                            if d.dt == "Item":
                                _item[d.field] = d.value
                        item_doc = frappe.get_doc(_item)
                        item_doc.insert()
                        item['item_code'] = item_doc.name
                else:
                    item['item_code'] = item.get('seller_item_code')
            
            pinv_doc.append("items", {
                'item_code': item.get('item_code'),
                'item_name': item.get('item_name'),
                'qty': flt(item.get("qty")),
                'rate': flt(item.get("net_price"))
            })
        
        pinv_doc.insert()
        frappe.db.commit()
        
        self.move_file(pinv_doc)
        
        # clean up the wizard
        frappe.db.sql("""
            UPDATE `tabSingles`
            SET 
                `value` = NULL
            WHERE
                `doctype` = "ZUGFeRD Wizard"
                AND `field` = "content_dict"
            ;""")
        frappe.db.sql("""
            UPDATE `tabSingles`
            SET 
                `value` = 0
            WHERE
                `doctype` = "ZUGFeRD Wizard"
                AND `field` = "ready_for_import"
            ;""")
        
        frappe.db.commit()
        
        return {
            'name': pinv_doc.name, 
            'url': get_url_to_form("Purchase Invoice", pinv_doc.name),
            'link': get_link_to_form("Purchase Invoice", pinv_doc.name)
        }

    def manual_purchase_invoice(self, company, supplier, date, bill_no, item, 
        amount, cost_center, taxes_and_charges, project=None, remarks=None, esr_code=None, payment_method=None):
        
        pinv = frappe.get_doc({
            'doctype': 'Purchase Invoice',
            'company': company,
            'supplier': supplier,
            'posting_date': date, 
            'project': project, 
            'bill_no': bill_no, 
            'cost_center': cost_center, 
            'taxes_and_charges': taxes_and_charges, 
            'terms': remarks,
            'remarks': remarks,
            'title': frappe.get_value("Supplier", supplier, "supplier_name"),
            'esr_reference_number': esr_code,
            'payment_type': payment_method
        })
        
        pinv.append("items", {
            'item_code': item,
            'qty': 1,
            'rate': amount,
            'amount': amount
        })
        
        taxes = frappe.get_doc("Purchase Taxes and Charges Template", taxes_and_charges)
        for t in taxes.taxes:
            pinv.append("taxes", t)
            
        pinv.set_missing_values()
        pinv.calculate_taxes_and_totals()
        pinv.flags.ignore_validate = True
        pinv.insert()
        
        self.move_file(pinv)
        
        frappe.db.commit()
        
        return {
            'name': pinv.name, 
            'url': get_url_to_form("Purchase Invoice", pinv.name),
            'link': get_link_to_form("Purchase Invoice", pinv.name)
        }
    
    def move_file(self, pinv_doc):
        # move file to new invoice
        frappe.db.sql("""
            UPDATE `tabFile`
            SET 
                `attached_to_name` = "{pinv}", 
                `attached_to_doctype` = "Purchase Invoice"
            WHERE
                `attached_to_name` = "ZUGFeRD Wizard"
                AND `attached_to_doctype` = "ZUGFeRD Wizard"
            ;""".format(pinv=pinv_doc.name))
            
        # clear wizard
        frappe.db.sql("""
            UPDATE `tabSingles`
            SET 
                `value` = NULL
            WHERE
                `doctype` = "ZUGFeRD Wizard"
                AND `field` = "file"
            ;""")
        return
