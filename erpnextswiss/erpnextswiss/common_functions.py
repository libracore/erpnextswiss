# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe

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
