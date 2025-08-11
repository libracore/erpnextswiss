# -*- coding: utf-8 -*-
#
# crm_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
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

# fetch the primary available address from a customer
@frappe.whitelist()
def get_primary_customer_address(customer):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = "Customer"
                   AND `tabDynamic Link`.`link_name` = "{customer}"
                   AND `tabDynamic Link`.`parenttype` = "Address"
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """.format(customer=customer)
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
            WHERE  `tabDynamic Link`.`link_doctype` = "Customer"
                   AND `tabDynamic Link`.`link_name` = "{customer}"
                   AND `tabDynamic Link`.`parenttype` = "Contact"
            ORDER BY `tabContact`.`is_primary_contact` DESC;
        """.format(customer=customer)
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
        
# fetch the first available address from a supplier
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

# fetch the primary available address from a supplier
@frappe.whitelist()
def get_primary_supplier_address(supplier):
    sql_query = u"""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = "Supplier"
                   AND `tabDynamic Link`.`link_name` = "{supplier}"
                   AND `tabDynamic Link`.`parenttype` = "Address"
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """.format(supplier=supplier)
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
            WHERE  `tabDynamic Link`.`link_doctype` = "Supplier"
                   AND `tabDynamic Link`.`link_name` = "{supplier}"
                   AND `tabDynamic Link`.`parenttype` = "Contact"
            ORDER BY `tabContact`.`is_primary_contact` DESC;
        """.format(supplier=supplier)
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

@frappe.whitelist()
def update_contact_first_and_last_name(contact, firstname, lastname):
    contact = frappe.get_doc("Contact", contact)
    contact.first_name = firstname
    contact.last_name = lastname
    contact.save()
	
@frappe.whitelist()
def change_customer_without_impact_on_price(dt, record, customer, address=None, contact=None):
    additional_updates = ''
    if address:
        additional_updates += ", `customer_address` = '{address}'".format(address=address)
    if contact:
        additional_updates += ", `contact_person` = '{contact}'".format(contact=contact)
    if dt == 'Quotation':
        update_query = """UPDATE `tab{dt}` SET `party_name` = '{customer}', `customer_name` = '{customer_name}'{additional_updates} WHERE `name` = '{record}'""".format(dt=dt, customer=customer, customer_name=frappe.get_doc("Customer", customer).customer_name, additional_updates=additional_updates, record=record)
    else:
        update_query = """UPDATE `tab{dt}` SET `customer` = '{customer}', `customer_name` = '{customer_name}'{additional_updates} WHERE `name` = '{record}'""".format(dt=dt, customer=customer, customer_name=frappe.get_doc("Customer", customer).customer_name, additional_updates=additional_updates, record=record)

    frappe.db.sql(update_query, as_list=True)
    return
