# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VATDeclaration(Document):
    def get_view_total(self, view_name, start_date, end_date):
        """ executes a tax lookup query for a total 
        
        """
        sql_query = ("""SELECT IFNULL(SUM(`base_grand_total`), 0) AS `total` 
                FROM `{0}` 
                WHERE `posting_date` >= '{1}' 
                AND `posting_date` <= '{2}'""".format(view_name, start_date, end_date))
        total = frappe.db.sql(sql_query, as_dict=True)
        #self.non_taxable_revenue = 123
        #self.save()
        return { 'total': total[0].total }

    def get_view_tax(self, view_name, start_date, end_date):
        """ executes a tax lookup query for a tax 
        
        """
        sql_query = ("""SELECT IFNULL(SUM(`total_taxes_and_charges`), 0) AS `total` 
                FROM `{0}` 
                WHERE `posting_date` >= '{1}' 
                AND `posting_date` <= '{2}'""".format(view_name, start_date, end_date))
        total = frappe.db.sql(sql_query, as_dict=True)
        return { 'total': total[0].total }
        
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
   
@frappe.whitelist()
def get_pretax(start_date, end_date):
    """ Extract pretax from paymment records
       
        Get sum of all amounts paid to tax account from purchase invoices
        Separates on the basis of the purchase tax template
    """
    vat_account = frappe.get_value('ERPNextSwiss VAT configuration', None, 'pretax_account')

    material_pretax_template = frappe.get_value('ERPNextSwiss VAT configuration', None, 'pretax_material_tax_template')
    sql_query = ("SELECT (IFNULL(SUM(`transactions`.`base_tax_amount`), 0)) AS `pretax` FROM ( " +
        "SELECT `t1`.`name`, `posting_date`, `account_head`, `base_tax_amount`, `t1`.`docstatus` " + 
        "FROM `tabPurchase Invoice` AS `t1` " +
        "INNER JOIN `tabPurchase Taxes and Charges` AS `t2` ON `t1`.`name` = `t2`.`parent` " +
        "WHERE `t1`.`docstatus` = 1 " +
        "AND `posting_date` >= '{0}' ".format(start_date) +
        "AND `posting_date` <= '{0}' ".format(end_date) +
        "AND `taxes_and_charges` = '{0}' ".format(material_pretax_template) + 
        "AND `account_head` = '{0}') AS `transactions`".format(vat_account))
    material_pretax = frappe.db.sql(sql_query, as_dict=True)
    
    # other_pretax_template = frappe.get_value('ERPNextSwiss VAT configuration', None, 'pretax_investment_tax_template')
    sql_query = ("SELECT (IFNULL(SUM(`transactions`.`base_tax_amount`), 0)) AS `pretax` FROM ( " +
        "SELECT `t1`.`name`, `posting_date`, `account_head`, `base_tax_amount`, `t1`.`docstatus` " + 
        "FROM `tabPurchase Invoice` AS `t1` " +
        "INNER JOIN `tabPurchase Taxes and Charges` AS `t2` ON `t1`.`name` = `t2`.`parent` " +
        "WHERE `t1`.`docstatus` = 1 " +
        "AND `posting_date` >= '{0}' ".format(start_date) +
        "AND `posting_date` <= '{0}' ".format(end_date) +
        "AND `taxes_and_charges` != '{0}' ".format(material_pretax_template) + 
        "AND `account_head` = '{0}') AS `transactions`".format(vat_account))
    other_pretax = frappe.db.sql(sql_query, as_dict=True)
        
    
    if material_pretax:
        material_pretax = material_pretax[0].pretax
    else:
        material_pretax = 0.0
    if other_pretax:
        other_pretax = other_pretax[0].pretax
    else:
        other_pretax = 0.0    
    
    return { 'material_pretax': material_pretax, 'other_pretax': other_pretax }
  
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
