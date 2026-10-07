# -*- coding: utf-8 -*-
#
# crm_tools.py
#
# Copyright (C) libracore, 2017-2026
# https://www.libracore.com or https://github.com/libracore
#

import frappe

# fetch the first available address from a customer
@frappe.whitelist()
def get_customer_address(customer):
    address_name = frappe.db.sql("""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = 'Customer'
        AND `link_name` = %(customer)s
        AND `parenttype` = 'Address';""",
        {
            'customer': customer
        }, as_dict=True
    )
    if address_name:
        if not frappe.db.exists("Address", address_name[0]['parent']):
            return None
        if not frappe.get_doc("Address", address_name[0]['parent']).check_permission():
            return None
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

# fetch the primary available address from a customer
@frappe.whitelist()
def get_primary_customer_address(customer):
    address_name = frappe.db.sql("""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Customer'
                   AND `tabDynamic Link`.`link_name` = %(customer)s
                   AND `tabDynamic Link`.`parenttype` = 'Address'
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """,
        {
            'customer': customer
        },
        as_dict=True
    )
    if address_name:
        if not frappe.db.exists("Address", address_name[0]['parent']):
            return None
        if not frappe.get_doc("Address", address_name[0]['parent']).check_permission():
            return None
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None
        
# fetch the primary available contact from a customer
@frappe.whitelist()
def get_primary_customer_contact(customer):
    contact_name = frappe.db.sql("""SELECT `tabDynamic Link`.`parent`, `tabContact`.`is_primary_contact`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabContact` ON `tabContact`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Customer'
                   AND `tabDynamic Link`.`link_name` = %(customer)s
                   AND `tabDynamic Link`.`parenttype` = 'Contact'
            ORDER BY `tabContact`.`is_primary_contact` DESC;
        """, 
        {
            'customer': customer
        },
        as_dict=True
    )
    if contact_name:
        if not frappe.db.exists("Contact", contact_name[0]['parent']):
            return None
        if not frappe.get_doc("Contact", contact_name[0]['parent']).check_permission():
            return None
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None

# fetch the first available contact from a customer
@frappe.whitelist()
def get_customer_contact(customer):
    contact_name = frappe.db.sql("""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = 'Customer'
        AND `link_name` = %(customer)s
        AND `parenttype` = 'Contact'
        """, 
        {
            'customer': customer
        },
        as_dict=True
    )
    if contact_name:
        if not frappe.db.exists("Contact", contact_name[0]['parent']):
            return None
        if not frappe.get_doc("Contact", contact_name[0]['parent']).check_permission():
            return None
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None
        
# fetch the first available address from a supplier
@frappe.whitelist()
def get_supplier_address(supplier):
    address_name = frappe.db.sql("""SELECT `parent` FROM `tabDynamic Link` WHERE
        `link_doctype` = 'supplier'
        AND `link_name` = %(supplier)s
        AND `parenttype` = 'Address';
        """, 
        {
            'supplier': supplier
        },
        as_dict=True
    )
    if address_name:
        if not frappe.db.exists("Address", address_name[0]['parent']):
            return None
        if not frappe.get_doc("Address", address_name[0]['parent']).check_permission():
            return None
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

# fetch the primary available address from a supplier
@frappe.whitelist()
def get_primary_supplier_address(supplier):
    address_name = frappe.db.sql("""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Supplier'
                   AND `tabDynamic Link`.`link_name` = %(supplier)s
                   AND `tabDynamic Link`.`parenttype` = 'Address'
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """, 
        {
            'supplier': supplier
        },
        as_dict=True
    )
    if address_name:
        if not frappe.db.exists("Address", address_name[0]['parent']):
            return None
        if not frappe.get_doc("Address", address_name[0]['parent']).check_permission():
            return None
        address = frappe.get_doc("Address", address_name[0]['parent'])
        return address
    else:
        return None

# fetch the primary available contact from a supplier
@frappe.whitelist()
def get_primary_supplier_contact(supplier):
    contact_name = frappe.db.sql("""SELECT `tabDynamic Link`.`parent`, `tabContact`.`is_primary_contact`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabContact` ON `tabContact`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = 'Supplier'
                   AND `tabDynamic Link`.`link_name` = %(supplier)s
                   AND `tabDynamic Link`.`parenttype` = 'Contact'
            ORDER BY `tabContact`.`is_primary_contact` DESC;
        """, 
        {
            'supplier': supplier
        },
        as_dict=True)
    if contact_name:
        if not frappe.db.exists("Contact", contact_name[0]['parent']):
            return None
        if not frappe.get_doc("Contact", contact_name[0]['parent']).check_permission():
            return None
        contact = frappe.get_doc("Contact", contact_name[0]['parent'])
        return contact
    else:
        return None
        
# fetch the primary available address from a customer
@frappe.whitelist()
def get_primary_company_address(company):
    address_name = frappe.db.sql("""SELECT `tabDynamic Link`.`parent`, `tabAddress`.`is_primary_address`
            FROM `tabDynamic Link` 
            LEFT JOIN `tabAddress` ON `tabAddress`.`name` = `tabDynamic Link`.`parent`
            WHERE  `tabDynamic Link`.`link_doctype` = "Company"
                   AND `tabDynamic Link`.`link_name` = %(company)s
                   AND `tabDynamic Link`.`parenttype` = "Address"
            ORDER BY `tabAddress`.`is_primary_address` DESC;
        """, 
        {
            'company': company
        }, 
        as_dict=True)
    if address_name:
        if not frappe.db.exists("Address", address_name[0]['parent']):
            return None
        if not frappe.get_doc("Address", address_name[0]['parent']).check_permission():
            return None
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
    if not frappe.db.exist("Doctype", dt):
        return
    if address:
        additional_updates += ", `customer_address` = %(address)s"
    if contact:
        additional_updates += ", `contact_person` = %(contact)s"
    if dt == 'Quotation':
        update_query = """
            UPDATE `tab{dt}` SET `party_name` = %(customer)s, `customer_name` = %(customer_name)s 
            {additional_updates} 
            WHERE `name` = %(record)s;""".format(dt=dt, additional_updates=additional_updates)
    else:
        update_query = """
            UPDATE `tab{dt}` SET `customer` = %(customer)s, `customer_name` = %(customer_name)s
            {additional_updates} 
            WHERE `name` = %(record)s;""".format(dt=dt, additional_updates=additional_updates)

    frappe.db.sql(update_query, 
        {
            'customer': customer, 
            'customer_name': frappe.get_doc("Customer", customer).customer_name, 
            'record': record
        },
        as_list=True)
    return
