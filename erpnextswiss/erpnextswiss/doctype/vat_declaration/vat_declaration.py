# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VATDeclaration(Document):
	pass

@frappe.whitelist()
def get_revenue(start_date, end_date, tax_mode=None):
    """ tax_mode: use None for all revenues or the configuration setting
                  e.g. abroad_tax_template
    """
    if tax_mode:  
        # get special taxed revenue
        tax_template = frappe.get_value('ERPNextSwiss VAT configuration', None, tax_mode)
        if tax_template:
            sql_query = ("SELECT IFNULL(SUM(`base_grand_total`), 0) AS `total_revenue` " +
                "FROM `tabSales Invoice` " +
                "WHERE `posting_date` >= '{0}' ".format(start_date) + 
                "AND `posting_date` <= '{0}' ".format(end_date) + 
                "AND `docstatus` = 1 " +
                "AND `taxes_and_charges` = '{0}'".format(tax_template))
            revenue = frappe.db.sql(sql_query, as_dict=True)
        else:
            revenue = None
    else:
        # get total revenue
        sql_query = ("SELECT IFNULL(SUM(`base_grand_total`), 0) AS `total_revenue` " +
            "FROM `tabSales Invoice` " +
            "WHERE `posting_date` >= '{0}' AND `posting_date` <= '{1}' AND `docstatus` = 1".format(
                start_date, end_date))
        revenue = frappe.db.sql(sql_query, as_dict=True)
        
    if revenue:
        return { 'revenue': revenue[0].total_revenue }
    else:
        # frappe.msgprint( _("No revenue found in the selected period.") )
        return { 'revenue': 0.0 } 
   
    
