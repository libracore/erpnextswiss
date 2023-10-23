# -*- coding: utf-8 -*-
# Copyright (c) 2020, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, getdate, cint, nowdate, add_days, get_link_to_form
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from frappe.utils.background_jobs import enqueue

@frappe.whitelist()
def calc_structur_organisation_totals(dt, dn):
    args = {
        'dt': dt,
        'dn': dn
    }
    enqueue("erpnextswiss.erpnextswiss.page.bkp_importer.utils._calc_structur_organisation_totals", queue='long', job_name='Calc HLK Totals {0}'.format(dn), timeout=1500, **args)
    return 'Calc HLK Totals {0}'.format(dn)

def _calc_structur_organisation_totals(dt, dn):
    parent_list = []
    last_elements = frappe.db.sql("""
        SELECT
            `hlk_element`,
            SUM(`amount`) AS `element_total`
         FROM `tab{dt} Item`
         WHERE
            `parent` = '{dn}'
        GROUP BY `hlk_element`;
    """.format(dt=dt, dn=dn), as_dict=True)
    
    last_element_names = []
    for last_element in last_elements:
        if last_element.hlk_element not in last_element_names:
            last_element_names.append(last_element.hlk_element)
            
            
    for last_element in last_elements:
        document = frappe.get_doc(dt, dn)
        for structur_element in document.hlk_structur_organisation:
            if structur_element.main_element == last_element.hlk_element:
                structur_element.total = last_element.element_total
                if dt != 'Sales Invoice':
                    structur_element.net_total = last_element.element_total
                if dt in ['Quotation', 'Sales Order']:
                    structur_element.charged = 0
                    
                direct_parent = structur_element.parent_element
                if direct_parent not in parent_list:
                    parent_list.append(direct_parent)
            else:
                if structur_element.main_element not in last_element_names:
                    structur_element.total = 0
        document.save()
    
    count = 0
    while parent_list and count < 10:
        count += 1
        parent_list = calc_and_create_new_parent_list(parent_list, dt, dn)
            
    return
        
def calc_and_create_new_parent_list(parent_list, dt, dn):
    for parent in parent_list:
        get_sum = frappe.db.sql("""
            SELECT
                IFNULL(SUM(`total`), 0) AS `element_total`
             FROM `tabHLK Structur Organisation`
             WHERE
                `parent` = '{dn}'
                AND `parent_element` = '{parent}';
        """.format(dn=dn, parent=parent), as_list=True)[0][0]
        
        document = frappe.get_doc(dt, dn)
        for structur_element in document.hlk_structur_organisation:
            if structur_element.main_element == parent:
                structur_element.total = get_sum
                if dt != 'Sales Invoice':
                    structur_element.net_total = get_sum
                if dt in ['Quotation', 'Sales Order']:
                    structur_element.charged = 0
                if structur_element.parent_element:
                    parent_list.append(structur_element.parent_element)
                parent_list.remove(parent)
        document.save()
    return parent_list
    
@frappe.whitelist()
def transfer_structur_organisation_discounts(dt, dn):
    args = {
        'dt': dt,
        'dn': dn
    }
    enqueue("erpnextswiss.erpnextswiss.page.bkp_importer.utils._transfer_structur_organisation_discounts", queue='long', job_name='transfer_structur_organisation_discounts {0}'.format(dn), timeout=1500, **args)
    return 'transfer_structur_organisation_discounts {0}'.format(dn)

@frappe.whitelist()
def _transfer_structur_organisation_discounts(dt, dn):
    document = frappe.get_doc(dt, dn)
    parent_elements = []
    sub_parent_elements = []
    
    for structur_element in document.hlk_structur_organisation:
        if not structur_element.parent_element:
            parent_elements.append(structur_element.main_element)
            
    for structur_element in document.hlk_structur_organisation:
        if structur_element.parent_element in parent_elements:
            sub_parent_elements.append(structur_element.main_element)
            
    for structur_element in document.hlk_structur_organisation:
        if not structur_element.parent_element in parent_elements:
            if not structur_element.main_element in sub_parent_elements:
                if structur_element.discounting:
                    if structur_element.discount_in_percent > 0:
                        for item in document.items:
                            if item.hlk_element == structur_element.main_element:
                                if not item.total_independent_price:
                                    if not item.variable_price:
                                        if item.margin_type not in ['Percentage', 'Amount']:
                                            item.discount_percentage = structur_element.discount_in_percent
                                            item.discount_amount = (item.price_list_rate / 100) * structur_element.discount_in_percent
                                            item.rate = item.price_list_rate - item.discount_amount
                                            item.net_rate = item.rate
                                            item.amount = item.rate * item.qty
                                            item.net_amount = item.amount
                                        else:
                                            item.discount_percentage = structur_element.discount_in_percent
                                            item.discount_amount = (item.rate_with_margin / 100) * structur_element.discount_in_percent
                                            item.rate = item.rate_with_margin - item.discount_amount
                                        if structur_element.show_discount:
                                            item.do_not_show_discount = 0
                                        else:
                                            item.do_not_show_discount = 1
                else:
                    structur_element.discount_in_percent = 0.00
                    structur_element.show_discount = 1
                    for item in document.items:
                        if item.hlk_element == structur_element.main_element:
                            if not item.total_independent_price:
                                if not item.variable_price:
                                    if item.margin_type not in ['Percentage', 'Amount']:
                                        item.discount_percentage = 0.00
                                        item.discount_amount = 0.00
                                        item.rate = item.price_list_rate
                                        item.net_rate = item.rate
                                        item.amount = item.rate * item.qty
                                        item.net_amount = item.amount
                                        item.do_not_show_discount = 0
                                    else:
                                        item.discount_percentage = 0.00
                                        item.discount_amount = 0.00
                                        item.rate = item.rate_with_margin
                                        item.net_rate = item.rate
                                        item.amount = item.rate_with_margin * item.qty
                                        item.net_amount = item.amount
                                        item.do_not_show_discount = 0
    document.save()
    
@frappe.whitelist()
def check_calc_valid_to_date():
    status = cint(frappe.db.get_single_value('HLK Settings', 'activate_automatic_validity_calculation'))
    if not status:
        return 'deactivated'
    else:
        default_months = cint(frappe.db.get_single_value('HLK Settings', 'default_validity_in_months'))
        return default_months
        
@frappe.whitelist()
def validate_hlk_element_allocation():
    status = cint(frappe.db.get_single_value('HLK Settings', 'validate_hlk_element_allocation'))
    if not status:
        return 'deactivated'
    else:
        return 'validate'
        
@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
    def postprocess(source, target):
        set_missing_values(source, target)
        #Get the advance paid Journal Entries in Sales Invoice Advance
        if target.get("allocate_advances_automatically"):
            target.set_advances()

    def set_missing_values(source, target):
        target.is_pos = 0
        target.ignore_pricing_rule = 1
        target.flags.ignore_permissions = True
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")

        # set company address
        target.update(get_company_address(target.company))
        if target.company_address:
            target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

        # set the redeem loyalty points if provided via shopping cart
        if source.loyalty_points and source.order_type == "Shopping Cart":
            target.redeem_loyalty_points = 1

    def update_item(source, target, source_parent):
        target.amount = source.amount_to_bill_now #flt(source.amount) - flt(source.billed_amt)
        target.base_amount = target.amount * flt(source_parent.conversion_rate)
        if source.amount_to_bill_now > 0:
            target.qty = target.amount / flt(source.rate) if (source.rate and source.amount_to_bill_now) else source.qty - source.returned_qty
        else:
            target.qty = 0

        if source_parent.project:
            target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
        if not target.cost_center and target.item_code:
            item = get_item_defaults(target.item_code, source_parent.company)
            item_group = get_item_group_defaults(target.item_code, source_parent.company)
            target.cost_center = item.get("selling_cost_center") \
                or item_group.get("selling_cost_center")

    doclist = get_mapped_doc("Sales Order", source_name, {
        "Sales Order": {
            "doctype": "Sales Invoice",
            "field_map": {
                "party_account_currency": "party_account_currency",
                "payment_terms_template": "payment_terms_template"
            },
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Sales Order Item": {
            "doctype": "Sales Invoice Item",
            "field_map": {
                "name": "so_detail",
                "parent": "sales_order",
            },
            "postprocess": update_item,
            "condition": lambda doc: doc.qty and (doc.base_amount==0 or abs(doc.billed_amt) < abs(doc.amount))
        },
        "Sales Taxes and Charges": {
            "doctype": "Sales Taxes and Charges",
            "add_if_empty": True
        },
        "Sales Team": {
            "doctype": "Sales Team",
            "add_if_empty": True
        }
    }, target_doc, postprocess, ignore_permissions=ignore_permissions)

    return doclist
    
@frappe.whitelist()
def check_for_changed_line_items(record):
    try:
        last_item_change = frappe.db.sql("""SELECT DISTINCT `modified` FROM `tabSales Order Item` WHERE `parent` = '{record}' LIMIT 1""".format(record=record), as_list=True)[0][0]
        last_record_change = frappe.db.sql("""SELECT `modified` FROM `tabSales Order` WHERE `name` = '{record}'""".format(record=record), as_list=True)[0][0]
        
        if last_item_change != last_record_change:
            document = frappe.get_doc('Sales Order', record)
            parent_elements = []
            sub_parent_elements = []
            
            for structur_element in document.hlk_structur_organisation:
                if not structur_element.parent_element:
                    parent_elements.append(structur_element.main_element)
                    
            for structur_element in document.hlk_structur_organisation:
                if structur_element.parent_element in parent_elements:
                    sub_parent_elements.append(structur_element.main_element)
                    
            for structur_element in document.hlk_structur_organisation:
                if not structur_element.parent_element in parent_elements:
                    if not structur_element.main_element in sub_parent_elements:
                        # without items with 'variable_price'
                        total_amount = flt(frappe.db.sql("""SELECT SUM(`amount`) FROM `tabSales Order Item` WHERE `hlk_element` = '{hlk_element}' AND `parent` = '{record}' AND `variable_price` = 0""".format(hlk_element=structur_element.main_element, record=record), as_list=True)[0][0])
                        total_charged = flt(frappe.db.sql("""SELECT SUM(`billed_amt`) FROM `tabSales Order Item` WHERE `hlk_element` = '{hlk_element}' AND `parent` = '{record}' AND `variable_price` = 0""".format(hlk_element=structur_element.main_element, record=record), as_list=True)[0][0])
                        if total_amount > 0:
                            charged_in_percent = (flt(100) / total_amount) * total_charged
                        else:
                            charged_in_percent = 0
                        structur_element.charged = charged_in_percent
                        
            for structur_element in document.hlk_structur_organisation:
                if structur_element.main_element in sub_parent_elements:
                    total_charged = 0
                    counter = 0
                    for _structur_element in document.hlk_structur_organisation:
                        if _structur_element.parent_element == structur_element.main_element:
                            total_charged += _structur_element.charged
                            counter += 1
                    structur_element.charged = total_charged / counter
                    
            for structur_element in document.hlk_structur_organisation:
                if structur_element.main_element in parent_elements:
                    total_charged = 0
                    counter = 0
                    for _structur_element in document.hlk_structur_organisation:
                        if _structur_element.parent_element == structur_element.main_element:
                            total_charged += _structur_element.charged
                            counter += 1
                    structur_element.charged = total_charged / counter
                    
            document.save()
            return 'changed'
        else:
            return 'unchanged'
    except:
        return 'unchanged'
        
@frappe.whitelist()
def set_amount_to_bill(record, element, value):
    document = frappe.get_doc("Sales Order", record)
    for item in document.items:
        if item.hlk_element == element:
            already_billed = item.billed_amt
            to_bill_now = ((flt(item.amount) / flt(100)) * flt(value)) - flt(already_billed)
            item.amount_to_bill_now = to_bill_now
    document.save()
    
@frappe.whitelist()
def get_item_group_for_structur_element_filter():
    return frappe.db.get_single_value('HLK Settings', 'structur_element_filter')
    
@frappe.whitelist()
def fetch_hlk_structur_organisation_table(template):
    template = frappe.get_doc("HLK Structur Organisation Template", template)
    return template.hlk_structur_organisation

@frappe.whitelist()
def is_calc_job_running(jobname):
    from frappe.utils.background_jobs import get_jobs
    running = get_info(jobname)
    return running

@frappe.whitelist()
def is_any_job_running(doctype, docname):
    running = 'refresh'
    if doctype == 'Quotation':
        jobname = 'Calc HLK Totals {0}'.format(docname)
        running = get_info(jobname)
        if running == 'refresh':
            jobname = 'transfer_structur_organisation_discounts {0}'.format(docname)
            running = get_info(jobname)
    if running == 'refresh':
        running = False
    else:
        running = True
    return running

def get_info(jobname):
    from rq import Queue, Worker
    from frappe.utils.background_jobs import get_redis_conn
    from frappe.utils import format_datetime, cint, convert_utc_to_user_timezone
    colors = {
        'queued': 'orange',
        'failed': 'red',
        'started': 'blue',
        'finished': 'green'
    }
    conn = get_redis_conn()
    queues = Queue.all(conn)
    workers = Worker.all(conn)
    jobs = []
    show_failed=False

    def add_job(j, name):
        if j.kwargs.get('site')==frappe.local.site:
            jobs.append({
                'job_name': j.kwargs.get('kwargs', {}).get('playbook_method') \
                    or str(j.kwargs.get('job_name')),
                'status': j.status, 'queue': name,
                'creation': format_datetime(convert_utc_to_user_timezone(j.created_at)),
                'color': colors[j.status]
            })
            if j.exc_info:
                jobs[-1]['exc_info'] = j.exc_info

    for w in workers:
        j = w.get_current_job()
        if j:
            add_job(j, w.name)

    for q in queues:
        if q.name != 'failed':
            for j in q.get_jobs(): add_job(j, q.name)

    if cint(show_failed):
        for q in queues:
            if q.name == 'failed':
                for j in q.get_jobs()[:10]: add_job(j, q.name)
    
    found_job = 'refresh'
    for job in jobs:
        if job['job_name'] == jobname:
            found_job = True

    return found_job
