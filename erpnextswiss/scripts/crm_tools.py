# -*- coding: utf-8 -*-
#
# crm_tools.py
#
# Copyright (C) libracore, 2017-2018
# https://www.libracore.com or https://github.com/libracore
#
# For information on ERPNext, refer to https://erpnext.org/
#

import frappe

# fetch the first available address from a customer
@frappe.whitelist()
def get_customer_address(customer):
    sql_query = u"""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = "Customer"
        AND `link_name` = "{customer}"
        AND `parenttype` = "Address"
        """.format(customer=customer)
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None
    
# fetch the first available contact from a customer
@frappe.whitelist()
def get_customer_contact(customer):
    sql_query = u"""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = "Customer"
        AND `link_name` = "{customer}"
        AND `parenttype` = "Contact"
        """.format(customer=customer)
    contact_name = frappe.db.sql(sql_query, as_dict=True)
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None

# fetch the first available address from a customer
@frappe.whitelist()
def get_supplier_address(supplier):
    sql_query = u"""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = "supplier"
        AND `link_name` = "{supplier}"
        AND `parenttype` = "Address"
        """.format(supplier=supplier)
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None
