# Copyright (c) 2024-2026, libracore and contributors
# For license information, please see license.txt
#
# Data provider for Google Looker Studio / libracore looker connector
#
import frappe
from frappe.utils import cint 
import urllib
from frappe.qb import DocType, Field

SENSITIVE_DOCTYPES = [
    'User', 
    'DocPerm', 
    'Custom DocPerm', 
    'User Permission',
    'Error Log',
    'Single',
    'Role',
    'DocType',
    'GL Entry',
    'Stock Ledger Entry',
    'Email Account',
    'Email Domain'
]

@frappe.whitelist()
def get_data(doctype, from_date=None, to_date=None, fields=None):
    # check access permission: token, user needs to have Report permission on this doctype
    if not has_report_permission(doctype):
        return {'error': 'No permission based on role model (report)'}
    # prevent sensitive doctypes from being accessed through Looker
    if doctype in SENSITIVE_DOCTYPES:
        return {'error': 'Access to sensitive doctype blocked.'}
    # unquote url-decoded doctype
    doctype = urllib.parse.unquote(doctype)
    
    # prepare fields filter
    fields_filter = "*"
    meta = frappe.get_meta(doctype)
    valid = {f.fieldname for f in meta.get_fields()} | {
        "name", "creation", "modified", "owner", "modified_by"
    }
    if fields:
        if type(fields) == str:
            fields=fields.split(",")
        
        for f in fields:
            if f no ind valid:
                return {'error': f"'{f}' is not a valid field on {doctype}"}
        fields_filter = "`{0}`".format("`, `".join(fields))
        
    if doctype == "Sales Order":
        data = get_sales_order_data(from_date, to_date, fields_filter)
    elif doctype == "Delivery Note":
        data = get_delivery_note_data(from_date, to_date, fields_filter)
    elif doctype == "Sales Invoice":
        data = get_sales_invoice_data(from_date, to_date, fields_filter)
    else:
        # fallback: return list
        table = DocType(doctype)
        
        if not fields:
            select_cols = [Field(f, table=table) for f in valid]
        else:
            select_cols = [Field(f, table=table) for f in fields]
        query = frappe.qb.from_(table).select(*select_cols)
        data = query.run(as_dict=True)

    return data
    
"""
Get all roles with report permission for a doctype
"""
def get_report_permissions(doctype):
    role_permissions = frappe.db.sql("""
        SELECT `role`
        FROM `tabDocPerm`
        WHERE 
            `parent` = %(doctype)s 
            AND `parenttype` = "DocType"
            AND `report` = 1
        UNION SELECT `role`
        FROM `tabCustom DocPerm`
        WHERE 
            `parent` = %(doctype)s 
            AND `parenttype` = "DocType"
            AND `report` = 1
        """,
        {
            'doctype': doctype
        }, 
        as_dict=True
    )
    roles = []
    for r in role_permissions:
        roles.append(r['role'])
        
    return roles
    
def has_report_permission(doctype):
    # get roles for current user
    roles = frappe.get_roles()
    # get all permissions on this doctype
    roles_with_report_permissions = get_report_permissions(doctype)
    # check if the current user has a role with report access
    report_permission = False
    for p in roles_with_report_permissions:
        if p in roles:
            report_permission = True
            break
            
    return report_permission
    
def get_sales_order_data(from_date=None, to_date=None, fields_filter="*"):
    conditions = ""
    if from_date:
        conditions += """ AND `tabSales Order`.`transaction_date` >= %(from_date)s """
    if to_date:
        conditions += """ AND `tabSales Order`.`transaction_date` <= %(to_date)s """
        
    sql_query = """
        SELECT {fields}
        FROM (
            SELECT 
                `tabSales Order`.*, 
                `tabCustomer`.`customer_group` AS `customer_customer_group`,
                `tabCustomer`.`territory` AS `customer_territory`
            FROM `tabSales Order`
            LEFT JOIN `tabCustomer` ON `tabCustomer`.`name` = `tabSales Order`.`customer`
            WHERE 
                `tabSales Order`.`docstatus` = 1
                {conditions}
        ) AS `raw`
        """.format(conditions=conditions, fields=fields_filter)
        
    data = frappe.db.sql(sql_query, 
        {
            'from_date': from_date,
            'to_date': to_date
        },
        as_dict=True
    )
    
    return data
        
def get_delivery_note_data(from_date=None, to_date=None, fields_filter="*"):
    conditions = ""
    if from_date:
        conditions += """ AND `tabDelivery Note`.`posting_date` >= "{from_date}" """.format(from_date=from_date)
    if to_date:
        conditions += """ AND `tabDelivery Note`.`posting_date` <= "{to_date}" """.format(to_date=to_date)
        
    sql_query = """
        SELECT {fields}
        FROM (
            SELECT 
                `tabDelivery Note`.*, 
                `tabCustomer`.`customer_group` AS `customer_customer_group`,
                `tabCustomer`.`territory` AS `customer_territory`
            FROM `tabDelivery Note`
            LEFT JOIN `tabCustomer` ON `tabCustomer`.`name` = `tabDelivery Note`.`customer`
            WHERE 
                `tabDelivery Note`.`docstatus` = 1
                {conditions}
        ) AS `raw`
        ;""".format(conditions=conditions, fields=fields_filter)
        
    data = frappe.db.sql(sql_query, as_dict=True)
    
    return data
    
def get_sales_invoice_data(from_date=None, to_date=None, fields_filter="*"):
    conditions = ""
    if from_date:
        conditions += """ AND `tabSales Invoice`.`posting_date` >= "{from_date}" """.format(from_date=from_date)
    if to_date:
        conditions += """ AND `tabSales Invoice`.`posting_date` <= "{to_date}" """.format(to_date=to_date)
        
    sql_query = """
        SELECT {fields}
        FROM (
            SELECT 
                `tabSales Invoice`.*, 
                `tabCustomer`.`customer_group` AS `customer_customer_group`,
                `tabCustomer`.`territory` AS `customer_territory`
            FROM `tabSales Invoice`
            LEFT JOIN `tabCustomer` ON `tabCustomer`.`name` = `tabSales Invoice`.`customer`
            WHERE 
                `tabSales Invoice`.`docstatus` = 1
                {conditions}
        ) AS `raw`
        ;""".format(conditions=conditions, fields=fields_filter)
        
    data = frappe.db.sql(sql_query, as_dict=True)
    
    return data
