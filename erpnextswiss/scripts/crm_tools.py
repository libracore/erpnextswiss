# -*- coding: utf-8 -*-
#
# crm_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
#

import frappe
from frappe import _

# fetch the first available address from a customer
@frappe.whitelist()
def get_customer_address(customer):
    sql_query = u"""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = 'Customer'
        AND `link_name` = '{customer}'
        AND `parenttype` = 'Address'
        """.format(customer=customer.replace("'", "''"))
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

# fetch the primary available address from a customer
@frappe.whitelist()
def get_primary_customer_address(customer):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Customer'
                   AND `tabDynamic Link`.`link_name` = '{customer}'
                   AND `tabDynamic Link`.`parenttype` = 'Address'
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """.format(customer=customer.replace("'", "''"))
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None
        
# fetch the primary available contact from a customer
@frappe.whitelist()
def get_primary_customer_contact(customer):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabContact`.`is_primary_contact`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabContact` ON `tabContact`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Customer'
                   AND `tabDynamic Link`.`link_name` = '{customer}'
                   AND `tabDynamic Link`.`parenttype` = 'Contact'
            ORDER BY `tabContact`.`is_primary_contact` DESC;
        """.format(customer=customer.replace("'", "''"))
    contact_name = frappe.db.sql(sql_query, as_dict=True)
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None

# fetch the first available contact from a customer
@frappe.whitelist()
def get_customer_contact(customer):
    sql_query = u"""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = 'Customer'
        AND `link_name` = '{customer}'
        AND `parenttype` = 'Contact'
        """.format(customer=customer.replace("'", "''"))
    contact_name = frappe.db.sql(sql_query, as_dict=True)
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None
        
# fetch the first available address from a supplier
@frappe.whitelist()
def get_supplier_address(supplier):
    sql_query = u"""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = 'supplier'
        AND `link_name` = '{supplier}'
        AND `parenttype` = 'Address'
        """.format(supplier=supplier.replace("'", "''"))
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

# fetch the primary available address from a supplier
@frappe.whitelist()
def get_primary_supplier_address(supplier):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Supplier'
                   AND `tabDynamic Link`.`link_name` = '{supplier}'
                   AND `tabDynamic Link`.`parenttype` = 'Address'
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """.format(supplier=supplier.replace("'", "''"))
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

# fetch the primary available contact from a supplier
@frappe.whitelist()
def get_primary_supplier_contact(supplier):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabContact`.`is_primary_contact`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabContact` ON `tabContact`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Supplier'
                   AND `tabDynamic Link`.`link_name` = '{supplier}'
                   AND `tabDynamic Link`.`parenttype` = 'Contact'
            ORDER BY `tabContact`.`is_primary_contact` DESC;
        """.format(supplier=supplier.replace("'", "''"))
    contact_name = frappe.db.sql(sql_query, as_dict=True)
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None
        
# fetch the primary available address from a customer
@frappe.whitelist()
def get_primary_company_address(company):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = "Company"
                   AND `tabDynamic Link`.`link_name` = "{company}"
                   AND `tabDynamic Link`.`parenttype` = "Address"
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """.format(company=company)
    address_name = frappe.db.sql(sql_query, as_dict=True)
    if address_name:
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

@frappe.whitelist(methods=["POST"])
def update_contact_first_and_last_name(contact, firstname, lastname):
    contact = frappe.get_doc("Contact", contact)
    contact.check_permission("write")
    contact.first_name = firstname
    contact.last_name = lastname
    contact.save()
	
@frappe.whitelist(methods=["POST"])
def change_customer_without_impact_on_price(dt, record, customer, address=None, contact=None):
    if dt not in ("Quotation", "Sales Order"):
        frappe.throw(_("Customer changes are only supported for quotations and sales orders."))

    transaction = frappe.get_doc(dt, record)
    transaction.check_permission("write")
    customer_doc = frappe.get_doc("Customer", customer)
    customer_doc.check_permission("read")

    updates = {
        "customer_name": customer_doc.customer_name,
    }
    if dt == "Quotation":
        updates["party_name"] = customer_doc.name
    else:
        updates["customer"] = customer_doc.name

    if address:
        address_doc = frappe.get_doc("Address", address)
        address_doc.check_permission("read")
        updates["customer_address"] = address_doc.name
    if contact:
        contact_doc = frappe.get_doc("Contact", contact)
        contact_doc.check_permission("read")
        updates["contact_person"] = contact_doc.name

    transaction.db_set(updates)
    return transaction.name
