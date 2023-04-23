# -*- coding: utf-8 -*-
# Copyright (c) 2017-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VATDeclaration(Document):
    pass

@frappe.whitelist()
def get_view_total(view_name, start_date, end_date, company=None):
    # try to fetch total from VAT query
    if frappe.db.exists("VAT query", view_name):
        sql_query = ("""SELECT IFNULL(SUM(`s`.`base_grand_total`), 0) AS `total` 
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
                query=frappe.get_value("VAT query", view_name, "query"),
                start_date=start_date, end_date=end_date).replace("{company}", company))        
    else:
        # fallback database view
        """ executes a tax lookup query for a total """
        sql_query = ("""SELECT IFNULL(SUM(`base_grand_total`), 0) AS `total` 
                FROM `{0}` 
                WHERE `posting_date` >= '{1}' 
                AND `posting_date` <= '{2}'""".format(view_name, start_date, end_date))
    # execute query
    try:
        total = frappe.db.sql(sql_query, as_dict=True)
    except Exception as err:
        frappe.log_error(err, "VAT declaration {0}".format(view_name))
        total = [{'total': 0}]
    return { 'total': total[0]['total'] }

@frappe.whitelist()
def get_view_tax(view_name, start_date, end_date, company=None):
    # try to fetch total from VAT query
    if frappe.db.exists("VAT query", view_name):
        sql_query = ("""SELECT IFNULL(SUM(`s`.`total_taxes_and_charges`), 0) AS `total` 
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
                query=frappe.get_value("VAT query", view_name, "query"),
                start_date=start_date, end_date=end_date).replace("{company}", company))      
    else:
        # fallback database view
        """ executes a tax lookup query for a tax """
        sql_query = ("""SELECT IFNULL(SUM(`total_taxes_and_charges`), 0) AS `total` 
                FROM `{0}` 
                WHERE `posting_date` >= '{1}' 
                AND `posting_date` <= '{2}'""".format(view_name, start_date, end_date))
    try:
        total = frappe.db.sql(sql_query, as_dict=True)
    except Exception as err:
        frappe.log_error(err, "VAT declaration {0}".format(view_name))
        total = [{'total': 0}]
    return { 'total': total[0]['total'] }
  
@frappe.whitelist()
def get_tax_rate(taxes_and_charges_template):
    sql_query = ("""SELECT `rate` 
        FROM `tabPurchase Taxes and Charges` 
        WHERE `parent` = '{0}' 
        ORDER BY `idx`;""".format(taxes_and_charges_template))
    result = frappe.db.sql(sql_query, as_dict=True)
    if result:
        return result[0].rate
    else:
        return 0
