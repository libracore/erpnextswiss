# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from erpnextswiss.erpnextswiss.jinja import get_week_from_date
from frappe.utils import cint, get_url_to_form, get_link_to_form, get_url_to_report, get_url_to_list, get_url_to_report_with_filters

# try to get building number from address line
def get_building_number(address_line):
    parts = address_line.strip().split(" ")
    if len(parts) > 1:
        return parts[-1]
    else:
        return ""
        
# get street name from address line
def get_street_name(address_line):
    parts = address_line.strip().split(" ")
    if len(parts) > 1:
        return " ".join(parts[:-1])
    else:
        return address_line

# split address line into street and building
def split_address_to_street_and_building(address_line):
    parts = address_line.split(" ")
    if len(parts) > 1:
        street = " ".join(parts[:-1])
        building = parts[-1]
        return street, building
    else:
        return address_line, ""

# get pincode from address line
def get_pincode(address_line):
    parts = address_line.strip().split(" ")
    if len(parts) > 1:
        return parts[0]
    else:
        return ""

# get city from address line
def get_city(address_line):
    parts = address_line.strip().split(" ")
    if len(parts) > 1:
        return " ".join(parts[1:])
    else:
        return address_line

# get primary address
# target types: Customer, Supplier, Company
@frappe.whitelist()
def get_primary_address(target_name, target_type="Customer"):
    sql_query = """SELECT 
            `tabAddress`.`address_line1`, 
            `tabAddress`.`address_line2`, 
            `tabAddress`.`pincode`, 
            `tabAddress`.`city`, 
            `tabAddress`.`county`,
            `tabAddress`.`country`, 
            UPPER(`tabCountry`.`code`) AS `country_code`, 
            `tabAddress`.`is_primary_address`
        FROM `tabDynamic Link` 
        LEFT JOIN `tabAddress` ON `tabDynamic Link`.`parent` = `tabAddress`.`name`
        LEFT JOIN `tabCountry` ON `tabAddress`.`country` = `tabCountry`.`name`
        WHERE `link_doctype` = '{type}' AND `link_name` = '{name}'
        ORDER BY `tabAddress`.`is_primary_address` DESC
        LIMIT 1;""".format(type=target_type, name=target_name)
    try:
        return frappe.db.sql(sql_query, as_dict=True)[0]
    except:
        return None

"""
    This function will compute a SCOR structured creditor reference from a regular reference of max. 21 alphanumeric characters
"""
@frappe.whitelist()
def get_scor_reference(reference):
    # length must not exceed 21 characters:
    ref_str = "{0}".format(reference)
    if len(ref_str) > 21:
        frappe.throw( _("Please provide a reference with max. 21 characters") )
    # compute reference code
    ref_code = ""
    for c in ref_str:
        if c in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ref_code += c
        elif c in ['A', 'a']:
            ref_code += "10"
        elif c in ['B', 'b']:
            ref_code += "11"
        elif c in ['C', 'c']:
            ref_code += "12"
        elif c in ['D', 'd']:
            ref_code += "13"
        elif c in ['E', 'e']:
            ref_code += "14"
        elif c in ['F', 'F']:
            ref_code += "15"
        elif c in ['G', 'g']:
            ref_code += "16"
        elif c in ['H', 'h']:
            ref_code += "17"
        elif c in ['I', 'i']:
            ref_code += "18"
        elif c in ['J', 'j']:
            ref_code += "19"
        elif c in ['K', 'k']:
            ref_code += "20"
        elif c in ['L', 'l']:
            ref_code += "21"
        elif c in ['M', 'm']:
            ref_code += "22"
        elif c in ['N', 'n']:
            ref_code += "23"
        elif c in ['O', 'o']:
            ref_code += "24"
        elif c in ['P', 'p']:
            ref_code += "25"
        elif c in ['Q', 'q']:
            ref_code += "26"
        elif c in ['R', 'r']:
            ref_code += "27"
        elif c in ['S', 's']:
            ref_code += "28"
        elif c in ['T', 't']:
            ref_code += "29"
        elif c in ['U', 'u']:
            ref_code += "30"
        elif c in ['V', 'v']:
            ref_code += "31"
        elif c in ['W', 'w']:
            ref_code += "32"
        elif c in ['X', 'x']:
            ref_code += "33"
        elif c in ['Y', 'y']:
            ref_code += "34"
        elif c in ['Z', 'z']:
            ref_code += "35"
        else:
            frappe.throw( _("Only valid alphanumeric characters are allowed: {0}").format(c))
    # add RF00 (= 27 15 0 0)
    ref_code += "271500"
    # compute modulo 97
    mod = int(ref_code) % 97
    # difference of 98 (97 plus 1, result must be 1) of mod is check digit
    check_digit = '{num:02d}'.format(num=(98 - mod))
    # return full code
    return "RF{check}{reference}".format(check=check_digit, reference=reference)

def get_recursive_item_groups(item_group):
    children = frappe.get_list("Item Group", filters={'parent_item_group': item_group}, fields=['name', 'is_group'])
    item_groups = [item_group]
    for c in children:
        if cint(c['is_group']) == 1:
            sub_groups = get_recursive_item_groups(c['name'])
            for s in sub_groups:
                if s not in item_groups:
                    item_groups.append(s)
        if c['name'] not in item_groups:
            item_groups.append(c['name'])
    return item_groups

@frappe.whitelist()
def url_to_form(doctype, docname):
    return get_url_to_form(doctype, docname)

@frappe.whitelist()
def link_to_form(doctype, docname):
    return get_link_to_form(doctype, docname)

@frappe.whitelist()
def link_to_list(doctype):
    return get_link_to_list(doctype)
    
@frappe.whitelist()
def url_to_report(name):
    return get_url_to_report(name)

@frappe.whitelist()
def url_to_report_with_filters(name, filters, report_type=None, doctype=None):
    return get_url_to_report(name, fitlers, report_type, doctype)
