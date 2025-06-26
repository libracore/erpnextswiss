# -*- coding: utf-8 -*-
# Copyright (c) 2017-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime

class VATDeclaration(Document):
    @frappe.whitelist()
    def create_transfer_file(self):
        tax_id = frappe.get_value("Company", self.company, "tax_id")
        if not tax_id or len(tax_id) < 12:
            frappe.throw( _("Tax ID/UID missing or invalid. Please configure for company {0}.").format(self.company) )
            
        data = {
            'uid': tax_id[3:].replace(".", "").replace("-", ""),
            'company': self.company,
            'generation_datetime': datetime.now(),
            'from_date': self.start_date,
            'to_date': self.end_date,
            'title': self.title,
            'z200': self.total_revenue,
            'z205': self.non_taxable_revenue,
            'z220': self.tax_free_services,
            'z221': self.revenue_abroad,
            'z225': self.transfers,
            'z230': self.non_taxable_services,
            'z235': self.losses,
            'z302': self.normal_amount,
            'z303': self.normal_amount_2024,
            'z312': self.reduced_amount,
            'z313': self.reduced_amount_2024,
            'z322': self.amount_1,
            'z323': self.amount_1_2024,
            'z332': self.amount_2,
            'z333': self.amount_2_2024,
            'z342': self.lodging_amount,
            'z343': self.lodging_amount_2024,
            'z382': self.additional_amount,
            'z383': self.additional_amount_2024,
            'z400': self.pretax_material,
            'z405': self.pretax_investments,
            'z410': self.missing_pretax,
            'z415': self.pretax_correction_mixed,
            'z420': self.pretax_correction_other,
            'z500': self.payable_tax,
            'z900': self.grants,
            'z910': self.donations,
            'acquisition_rate': 7.7 if self.start_date < "2024-01-01" else 8.1,
            'rate1': self.rate_1,
            'rate1_2024': self.rate_1,
            'rate2': self.rate_2,
            'rate2_2024': self.rate_2
        }
        # render file
        if self.vat_type == "flat":
            template = 'erpnextswiss/templates/xml/taxes_net.html'
        else:
            template = 'erpnextswiss/templates/xml/taxes_effective.html'
        content = frappe.render_template(template, data)
        return { 'content': content }

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
        total = frappe.db.sql(sql_query, as_dict=True)
    else:
        # table missing, skip
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
        total = frappe.db.sql(sql_query, as_dict=True)
    else:
        # table missing, skip
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
