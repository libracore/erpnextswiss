# Copyright (c) 2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import calendar
import datetime
from frappe.utils import cint

def execute(filters=None):
    columns, data = [], []
            
    columns = get_columns()
    
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {'fieldname': 'customer', 'label': _('Customer'), 'fieldtype': 'Link', 'options': 'Customer', 'width': 75},
        {'fieldname': 'customer_name', 'label': _('Customer name'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'date', 'label': _('Date'), 'fieldtype': 'Date', 'width': 80},
        {'fieldname': 'project', 'label': _('Project'), 'fieldtype': 'Link', 'options': 'Project', 'width': 150},
        {'fieldname': 'item', 'label': _('Item'), 'fieldtype': 'Link', 'options': 'Item', 'width': 200},
        {'fieldname': 'hours', 'label': _('Billing Hours'), 'fieldtype': 'Float', 'width': 100},
        {'fieldname': 'qty', 'label': _('Qty'), 'fieldtype': 'Float', 'width': 50},
        {'fieldname': 'rate', 'label': _('Rate'), 'fieldtype': 'Currency', 'width': 100},
        {'fieldname': 'reference', 'label': _('Reference'), 'fieldtype': 'Dynamic Link', 'options': 'dt', 'width': 120},
        {'fieldname': 'action', 'label': _('Action'), 'fieldtype': 'Data', 'width': 150}
    ]
    
def get_data(filters):
    entries = get_invoiceable_entries(from_date=filters.from_date, to_date=filters.to_date, customer=filters.customer)
    
    # find customers
    customers = []
    for e in entries:
        if e.customer not in customers:
            customers.append(e.customer)
    
    # create grouped entries
    output = []
    for c in customers:
        details = []
        total_h = 0
        total_amount = 0
        customer_name = None
        for e in entries:
            if e.customer == c:
                total_h += e.hours or 0
                total_amount += ((e.qty or 1) * (e.rate or 0))
                customer_name = e.customer_name
                details.append(e)
                
        # insert customer row
        prefix = ""
        if "natascha" in frappe.session.user:
            prefix = "&#129412; "
        output.append({
            'customer': c,
            'customer_name': customer_name,
            'hours': total_h,
            'qty': 1,
            'rate': total_amount,
            'action': prefix + _('Create invoice'),
            'indent': 0
        })
        for d in details:
            output.append(d)
            
    return output

def get_invoiceable_entries(from_date=None, to_date=None, customer=None):
    if not from_date:
        from_date = "2000-01-01"
    if not to_date:
        to_date = "2099-12-31"

    if not customer:
        customer = "%"
    
    invoicing_item = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "service_item")
    if not invoicing_item:
        frappe.throw( _("Invoicing configuration is missing the invoice item. Please set under ERPNextSwiss Settings > Invoice Item."), _("Configuration missing") )
    invoicing_method = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "invoice_method") or "hours"
    
    sql_query = """
        SELECT 
            `tabProject`.`customer` AS `customer`,
            `tabCustomer`.`customer_name` AS `customer_name`,
            DATE(`tabTimesheet Detail`.`from_time`) AS `date`,
            "Timesheet"  AS `dt`,
            `tabTimesheet`.`name` AS `reference`,
            `tabTimesheet`.`employee_name` AS `employee_name`,
            `tabTimesheet Detail`.`name` AS `detail`,
            `tabProject`.`name` AS `project`,
            "{invoicing_item}" AS `item`,
            `tabTimesheet Detail`.`{method}` AS `hours`,
            1 AS `qty`,
            NULL AS `rate`,
            `tabTimesheet Detail`.`remarks` AS `remarks`,
            1 AS `indent`
        FROM `tabTimesheet Detail`
        LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tabTimesheet Detail`.`parent`
        LEFT JOIN `tabSales Invoice Item` ON (
            `tabTimesheet Detail`.`name` = `tabSales Invoice Item`.`ts_detail`
            AND `tabSales Invoice Item`.`docstatus` < 2
        )
        LEFT JOIN `tabProject` ON `tabProject`.name = `tabTimesheet Detail`.`project`
        LEFT JOIN `tabCustomer` ON `tabCustomer`.`name` = `tabProject`.`customer`
        WHERE 
           `tabTimesheet`.`docstatus` = 1
           AND `tabCustomer`.`name` LIKE "{customer}"
           AND ((DATE(`tabTimesheet Detail`.`from_time`) >= "{from_date}" AND DATE(`tabTimesheet Detail`.`from_time`) <= "{to_date}")
            OR (DATE(`tabTimesheet Detail`.`to_time`) >= "{from_date}" AND DATE(`tabTimesheet Detail`.`to_time`) <= "{to_date}"))
           AND `tabSales Invoice Item`.`name` IS NULL
           AND `tabTimesheet Detail`.`{method}` > 0
           
        UNION SELECT
            `tabDelivery Note`.`customer` AS `customer`,
            `tabDelivery Note`.`customer_name` AS `customer_name`,
            `tabDelivery Note`.`posting_date` AS `date`,
            "Delivery Note" AS `dt`,
            `tabDelivery Note`.`name` AS `reference`,
            NULL AS `employee_name`,
            `tabDelivery Note Item`.`name` AS `detail`,
            `tabDelivery Note`.`project` AS `project`,
            `tabDelivery Note Item`.`item_code` AS `item`,
            NULL AS `hours`,
            `tabDelivery Note Item`.`qty` AS `qty`,
            `tabDelivery Note Item`.`net_rate` AS `rate`,
            `tabDelivery Note`.`name` AS `remarks`,
            1 AS `indent`
        FROM `tabDelivery Note Item`
        LEFT JOIN `tabDelivery Note` ON `tabDelivery Note`.`name` = `tabDelivery Note Item`.`parent`
        LEFT JOIN `tabSales Invoice Item` ON (
            `tabDelivery Note Item`.`name` = `tabSales Invoice Item`.`dn_detail`
            AND `tabSales Invoice Item`.`docstatus` < 2
        )
        WHERE 
            `tabDelivery Note`.`docstatus` = 1
            AND `tabDelivery Note`.`customer` LIKE "{customer}"
            AND (`tabDelivery Note`.`posting_date` >= "{from_date}" AND `tabDelivery Note`.`posting_date` <= "{to_date}")
            AND `tabSales Invoice Item`.`name` IS NULL
                    
        ORDER BY `customer_name` ASC, `date` ASC;
    """.format(from_date=from_date, to_date=to_date, invoicing_item=invoicing_item, customer=customer, method=invoicing_method)
    entries = frappe.db.sql(sql_query, as_dict=True)
    return entries

@frappe.whitelist()
def create_invoice(from_date, to_date, customer, company=None):
    # fetch entries
    entries = get_invoiceable_entries(from_date=from_date, to_date=to_date, customer=customer)
    
    # create sales invoice
    sinv = frappe.get_doc({
        'doctype': "Sales Invoice",
        'customer': customer,
        'customer_group': frappe.get_value("Customer", customer, "customer_group")
    })
    
    for e in entries:
        #Format Remarks 
        if e.remarks:
            remarkstring = "{0}: {1}<br>{2}".format(e.date.strftime("%d.%m.%Y"), e.employee_name, e.remarks)
        else:
            remarkstring = "{0}: {1}".format(e.date.strftime("%d.%m.%Y"), e.employee_name)
        
        # project trace
        sinv.project = e.project
        
        item = {
            'item_code': e.item,
            'qty': e.qty,
            'rate': e.rate,
            'description': e.remarks,            # will be overwritten by frappe
            'remarks': remarkstring

        }
        if e.dt == "Delivery Note":
            item['delivery_note'] = e.reference
            item['dn_detail'] = e.detail

        elif e.dt == "Timesheet":
            item['timesheet'] = e.reference
            item['ts_detail'] = e.detail
            item['qty'] = e.hours
     
        if item['qty'] > 0:                     # only append items with qty > 0 (otherwise this will cause an error)
            sinv.append('items', item)
    
    # check currency and debtors account
    customer_doc = frappe.get_doc("Customer", customer)
    if customer_doc.default_currency:
        sinv.currency = customer_doc.default_currency
    
    # assume debtors account from first row (#NOTE TO FUTURE SELF: INCLUDE MULTI-COMPANY)
    if customer_doc.accounts and len(customer_doc.accounts) > 0:
        if company:
            for a in customer_doc.accounts:
                if a.company == company:
                    sinv.debit_to = a.account
        else:
            sinv.debit_to = customer_doc.accounts[0].account
    
    # add default taxes and charges
    taxes = find_tax_template(customer)
    if taxes:
        sinv.taxes_and_charges = taxes
        taxes_template = frappe.get_doc("Sales Taxes and Charges Template", taxes)
        for t in taxes_template.taxes:
            sinv.append("taxes", t)
    
    # insert new invoice
    sinv.insert()
    
    frappe.db.commit()
    
    return sinv.name

def find_tax_template(customer):
    # check if the customer has a specific template
    customer_doc = frappe.get_doc("Customer", customer)
    if customer_doc.get("default_taxes_and_charges"):
        template = customer_doc.get("default_taxes_and_charges")
    else:
        default_template = frappe.get_all("Sales Taxes and Charges Template", 
            filters={
                'is_default': 1
            }, 
            fields=['name'])
        if len(default_template) > 0:
            template = default_template[0]['name']
        else:
            template = None
    return template
