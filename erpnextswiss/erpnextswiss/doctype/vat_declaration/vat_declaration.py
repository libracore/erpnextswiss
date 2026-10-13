# -*- coding: utf-8 -*-
# Copyright (c) 2017-2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt
from datetime import datetime

DEDUCTION_FIELDS = ("tax_free_services", "revenue_abroad", "transfers", "non_taxable_services", "losses", "misc")
# (amount, rate, tax)
EFFECTIVE_TAX_LINES = (
    ("normal_amount_2024", "normal_rate_2024", "normal_tax_2024"),
    ("reduced_amount_2024", "reduced_rate_2024", "reduced_tax_2024"),
    ("lodging_amount_2024", "lodging_rate_2024", "lodging_tax_2024"),
    ("normal_amount", "normal_rate", "normal_tax"),
    ("reduced_amount", "reduced_rate", "reduced_tax"),
    ("lodging_amount", "lodging_rate", "lodging_tax"),
)
FLAT_TAX_LINES = (
    ("amount_1_2024", "rate_1_2024", "tax_1_2024"),
    ("amount_2_2024", "rate_2_2024", "tax_2_2024"),
    ("amount_1", "rate_1", "tax_1"),
    ("amount_2", "rate_2", "tax_2"),
)


class VATDeclaration(Document):
    def validate(self):
        self.calculate()

    @frappe.whitelist()
    def calculate(self):
        self.total_deductions = sum(flt(self.get(f)) for f in DEDUCTION_FIELDS)
        self.taxable_revenue = flt(self.total_revenue) - flt(self.non_taxable_revenue) - self.total_deductions
        for amount, rate, tax in EFFECTIVE_TAX_LINES + FLAT_TAX_LINES:
            self.set(tax, flt(self.get(amount)) * flt(self.get(rate)) / 100)
        self.total_tax = (sum(flt(self.get(line[2])) for line in EFFECTIVE_TAX_LINES + FLAT_TAX_LINES)
            + flt(self.additional_tax_2024) + flt(self.additional_tax))
        self.total_pretax_reductions = (flt(self.pretax_material) + flt(self.pretax_investments)
            + flt(self.missing_pretax) - flt(self.pretax_correction_mixed) - flt(self.pretax_correction_other)
            + flt(self.form_1050) + flt(self.form_1055))
        self.payable_tax = self.total_tax - self.total_pretax_reductions

    @frappe.whitelist()
    def get_values(self):
        totals = {
            'total_revenue': "200",
            'tax_free_services': "220",
            'revenue_abroad': "221",
            'transfers': "225",
            'non_taxable_services': "230",
            'losses': "235",
            'additional_amount_2024': "383",
            'additional_amount': "382"
        }
        taxes = {'additional_tax_2024': "383", 'additional_tax': "382"}
        if self.vat_type == "effective":
            totals.update({'normal_amount_2024': "303", 'reduced_amount_2024': "313", 'lodging_amount_2024': "343",
                'normal_amount': "302", 'reduced_amount': "312", 'lodging_amount': "342"})
            taxes.update({'pretax_material': "400", 'pretax_investments': "405"})
        else:
            totals.update({'amount_1_2024': "323", 'amount_2_2024': "333", 'amount_1': "322", 'amount_2': "332"})

        for column, fields in (("base_grand_total", totals), ("total_taxes_and_charges", taxes)):
            for fieldname, code in fields.items():
                self.set(fieldname, get_view_sum("viewVAT_" + code, column, self.start_date, self.end_date, self.company))
        self.calculate()

    @frappe.whitelist()
    def create_transfer_file(self):
        tax_id = frappe.get_value("Company", self.company, "tax_id")
        if not tax_id or len(tax_id) < 12:
            frappe.throw( _("Tax ID/UID missing or invalid. Please configure for company {0}.").format(self.company) )
            
        data = {
            'uid': (tax_id[3:].replace(".", "").replace("-", "")).strip(),
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
            'z400': self.pretax_material,
            'z405': self.pretax_investments,
            'z410': self.missing_pretax,
            'z415': self.pretax_correction_mixed,
            'z420': self.pretax_correction_other,
            'z500': self.payable_tax,
            'z900': self.grants,
            'z910': self.donations,
            'rate1': self.rate_1,
            'rate1_2024': self.rate_1,
            'rate2': self.rate_2,
            'rate2_2024': self.rate_2,
            'acquisition_taxes': [{
                'rate': 7.7 if str(self.start_date) < "2024-01-01" else 8.1,
                'turnover': self.additional_amount_2024 or self.additional_amount
            }]
        }
        # render file
        if self.vat_type == "flat":
            template = 'erpnextswiss/templates/xml/taxes_net.html'
        else:
            template = 'erpnextswiss/templates/xml/taxes_effective.html'
        content = frappe.render_template(template, data)
        return { 'content': content }

def get_view_sum(view_name, column, start_date, end_date, company):
    # try to fetch total from VAT query
    if not frappe.db.exists("VAT query", view_name):
        return 0
    sql_query = ("""SELECT IFNULL(SUM(`s`.`{column}`), 0) AS `total`
            FROM ({query}) AS `s`
            WHERE `s`.`posting_date` >= '{start_date}'
            AND `s`.`posting_date` <= '{end_date}'""".format(
            column=column, query=frappe.get_value("VAT query", view_name, "query"),
            start_date=start_date, end_date=end_date).replace("{company}", company))
    return frappe.db.sql(sql_query)[0][0]

@frappe.whitelist()
def get_view_total(view_name, start_date, end_date, company=None):
    return { 'total': get_view_sum(view_name, "base_grand_total", start_date, end_date, company) }

@frappe.whitelist()
def get_view_tax(view_name, start_date, end_date, company=None):
    return { 'total': get_view_sum(view_name, "total_taxes_and_charges", start_date, end_date, company) }

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
