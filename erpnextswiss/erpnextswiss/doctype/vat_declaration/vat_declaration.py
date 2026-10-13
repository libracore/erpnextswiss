# -*- coding: utf-8 -*-
# Copyright (c) 2017-2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt
from datetime import datetime

# from this date on, net and flat tax rate declarations use the eCH-0217 simpleTaxRateMethod
SIMPLE_METHOD_START = "2025-01-01"
# deductions from total revenue (220-280)
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
        self.check_activities_turnover()

    def check_activities_turnover(self):
        # from 2025, taxable revenue (299) must be fully assigned to activities, e.g. a missing code or VAT query shows here
        difference = flt(self.taxable_revenue - self.activities_turnover, 2)
        if self.vat_type == "flat" and self.is_simple_method() and difference:
            frappe.msgprint(_("Taxable revenue (299) differs from the supplies according to the calculation sheet by {0}.").format(
                frappe.format(difference, {'fieldtype': "Currency"})), indicator="orange", title=_("Warning"))

    def is_simple_method(self):
        return str(self.start_date or "") >= SIMPLE_METHOD_START

    @frappe.whitelist()
    def calculate(self):
        simple = self.is_simple_method()
        flat = self.vat_type == "flat"
        self.total_deductions = sum(flt(self.get(f)) for f in DEDUCTION_FIELDS)
        # non-taxable revenue (205) only exists in the effective method
        self.taxable_revenue = flt(self.total_revenue) - (0 if flat else flt(self.non_taxable_revenue)) - self.total_deductions

        # legacy fields: rate on net (effective) or gross (net tax rate) amount
        for amount, rate, tax in EFFECTIVE_TAX_LINES + FLAT_TAX_LINES:
            self.set(tax, flt(self.get(amount)) * flt(self.get(rate)) / 100)
        # from 2025: tax is rounded per row and then summed, as in the ESTV calculation sheet
        for row in self.activities + self.acquisition_taxes:
            row.tax = flt(flt(row.turnover) * flt(row.rate) / 100, 2)
        self.activities_turnover = flt(sum(flt(r.turnover) for r in self.activities), 2)
        self.activities_tax = flt(sum(r.tax for r in self.activities), 2)
        # average rate is for display only
        self.average_rate = 100 * self.activities_tax / self.activities_turnover if self.activities_turnover else 0

        # from 2025, flat declarations use the activities and acquisition tax tables instead of the legacy fields
        tax_lines = EFFECTIVE_TAX_LINES if not flat else (() if simple else FLAT_TAX_LINES)
        self.total_tax = sum(flt(self.get(line[2])) for line in tax_lines)
        if simple:
            self.total_tax += sum(r.tax for r in self.acquisition_taxes) + (self.activities_tax if flat else 0)
        else:
            self.total_tax += flt(self.additional_tax_2024) + flt(self.additional_tax)

        self.total_pretax_reductions = (flt(self.pretax_material) + flt(self.pretax_investments)
            + flt(self.missing_pretax) - flt(self.pretax_correction_mixed) - flt(self.pretax_correction_other)
            # forms 1050/1055 (470/471) were abolished in 2025
            + (0 if simple else flt(self.form_1050) + flt(self.form_1055)))
        self.payable_tax = self.total_tax - self.total_pretax_reductions

    @frappe.whitelist()
    def get_values(self):
        simple = self.is_simple_method()
        # field: VAT query code, summed over base_grand_total
        totals = {
            'total_revenue': "200",
            'tax_free_services': "220",
            'revenue_abroad': "221",
            'transfers': "225",
            'non_taxable_services': "230",
            'losses': "235",
            'misc': "280",
            'grants': "900",
            'donations': "910"
        }
        # field: VAT query code, summed over total_taxes_and_charges
        taxes = {}
        if self.vat_type == "effective":
            totals.update({'normal_amount_2024': "303", 'reduced_amount_2024': "313", 'lodging_amount_2024': "343",
                'normal_amount': "302", 'reduced_amount': "312", 'lodging_amount': "342"})
            taxes.update({'pretax_material': "400", 'pretax_investments': "405"})
        elif not simple:
            totals.update({'amount_1_2024': "323", 'amount_2_2024': "333", 'amount_1': "322", 'amount_2': "332"})
        if not simple:
            totals.update({'additional_amount_2024': "383", 'additional_amount': "382"})
            taxes.update({'additional_tax_2024': "383", 'additional_tax': "382"})

        templates = self.get_code_templates()
        turnovers = self.get_template_turnovers([t.name for t in templates])
        self.set_code_totals(templates, turnovers, {code: field for field, code in totals.items()})

        for column, fields in (("base_grand_total", totals), ("total_taxes_and_charges", taxes)):
            for fieldname, code in fields.items():
                view_name = "viewVAT_" + code
                # VAT queries take precedence over Item Tax Template codes and manually entered values
                if frappe.db.exists("VAT query", view_name):
                    self.set(fieldname, self.get_view_sum(view_name, column))

        # from 2025: turnover per activity and acquisition tax rate from the VAT queries in the table rows
        if simple:
            activity_templates = [t for t in templates if t.vat_declaration_code == "Calculation sheet"]
            if self.vat_type == "flat" and activity_templates:
                self.set_activities(activity_templates, turnovers)
            elif self.vat_type == "flat":
                self.update_table("activities", ["activity_id", "description", "rate", "vat_query"])
            self.update_table("acquisition_taxes", ["rate", "vat_query"])
        self.calculate()

    def get_view_sum(self, view_name, column="base_grand_total"):
        return get_view_sum(view_name, column, self.start_date, self.end_date, self.company)

    def get_code_templates(self):
        return frappe.get_all("Item Tax Template",
            filters={'company': self.company, 'vat_declaration_code': ["is", "set"]},
            fields=["name", "title", "vat_declaration_code", "vat_description", "flat_tax_rate", "estv_activity_id"],
            order_by="title")

    def get_template_turnovers(self, templates):
        if not templates:
            return {}
        items = frappe.db.sql("""
            SELECT `sii`.`item_tax_template`, `sii`.`base_net_amount`, `sii`.`item_tax_rate`
            FROM `tabSales Invoice Item` AS `sii`
            JOIN `tabSales Invoice` AS `si` ON `si`.`name` = `sii`.`parent`
            WHERE `si`.`docstatus` = 1
              AND `si`.`company` = %(company)s
              AND `si`.`posting_date` BETWEEN %(start_date)s AND %(end_date)s
              AND `sii`.`item_tax_template` IN %(templates)s""",
            {'company': self.company, 'start_date': self.start_date, 'end_date': self.end_date, 'templates': templates},
            as_dict=True)
        turnovers = {}
        for item in items:
            # gross amount based on the tax rates recorded on the invoice, so later rate changes do not affect past periods
            rate = sum(flt(r) for r in json.loads(item.item_tax_rate or "{}").values())
            turnovers[item.item_tax_template] = turnovers.get(item.item_tax_template, 0) + flt(item.base_net_amount) * (1 + rate / 100)
        return turnovers

    def set_code_totals(self, templates, turnovers, code_fields):
        # only fields with at least one Item Tax Template code are set, all codes except 900/910 count towards 200
        totals = {}
        for t in templates:
            amount = turnovers.get(t.name, 0)
            codes = [t.vat_declaration_code] + ([] if t.vat_declaration_code in ("900", "910") else ["200"])
            for code in codes:
                if code in code_fields:
                    totals[code] = totals.get(code, 0) + amount
        for code, amount in totals.items():
            self.set(code_fields[code], flt(amount, 2))

    def set_activities(self, templates, turnovers):
        # one row per Item Tax Template with turnover, a VAT query on a row overrides its turnover
        queries = {r.item_tax_template: r.vat_query for r in self.activities if r.item_tax_template}
        rows = [r.as_dict(no_default_fields=True) for r in self.activities if not r.item_tax_template]
        for t in templates:
            rows.append(frappe._dict({
                'item_tax_template': t.name,
                'activity_id': t.estv_activity_id,
                'description': t.vat_description or t.title,
                'rate': t.flat_tax_rate,
                'vat_query': queries.get(t.name),
                'turnover': flt(turnovers.get(t.name, 0), 2)
            }))
        for row in rows:
            if row.vat_query:
                row.turnover = self.get_view_sum(row.vat_query)
        self.set("activities", [r for r in rows if not r.item_tax_template or flt(r.turnover, 2)])

    def update_table(self, table, fields):
        # rows are configuration (rate, VAT query, ...) carried over from the previous declaration
        if not self.get(table):
            previous = frappe.get_all("VAT Declaration",
                filters={'company': self.company, 'docstatus': ["<", 2], 'start_date': ["<", self.start_date]},
                order_by="start_date desc", limit=1, pluck="name")
            if previous:
                self.set(table, frappe.get_all(frappe.get_meta(self.doctype).get_field(table).options,
                    filters={'parent': previous[0], 'parenttype': self.doctype, 'parentfield': table},
                    fields=fields, order_by="idx"))
        for row in self.get(table):
            if row.vat_query:
                row.turnover = self.get_view_sum(row.vat_query)

    # activities for the XML, cumulated per ESTV activity ID and rate
    def get_supplies(self):
        # the ESTV only accepts its own 5-character activity IDs
        invalid = ["#{0} {1}".format(r.idx, r.description or "") for r in self.activities
            if flt(r.turnover) and len((r.activity_id or "").strip()) != 5]
        if invalid:
            frappe.throw(_("ESTV activity ID missing or invalid (5 characters) for: {0}").format(", ".join(invalid)))
        supplies = {}
        for r in self.activities:
            if flt(r.turnover):
                key = (r.activity_id.strip(), flt(r.rate))
                supplies[key] = supplies.get(key, 0) + flt(r.turnover)
        return [{'activity_id': a, 'rate': rate, 'turnover': turnover} for (a, rate), turnover in supplies.items()]

    @frappe.whitelist()
    def create_transfer_file(self):
        tax_id = frappe.get_value("Company", self.company, "tax_id")
        if not tax_id or len(tax_id) < 12:
            frappe.throw( _("Tax ID/UID missing or invalid. Please configure for company {0}.").format(self.company) )
            
        simple = self.is_simple_method()
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
            'z280': self.misc,
            'misc_description': (self.misc_description or _("Miscellaneous"))[:50],
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
            'rate1_2024': self.rate_1_2024,
            'rate2': self.rate_2,
            'rate2_2024': self.rate_2_2024
        }
        # acquisition tax: one entry per rate from 2025, a single legacy rate before
        if simple:
            data['acquisition_taxes'] = [{'rate': r.rate, 'turnover': r.turnover} for r in self.acquisition_taxes]
        else:
            data['acquisition_taxes'] = [{
                'rate': 7.7 if str(self.start_date) < "2024-01-01" else 8.1,
                'turnover': self.additional_amount_2024 or self.additional_amount
            }]
        # render file
        # from 2025, net and flat tax rate methods share the eCH-0217 simpleTaxRateMethod
        if self.vat_type == "flat" and simple:
            data['supplies'] = self.get_supplies()
            template = 'erpnextswiss/templates/xml/taxes_simple.html'
        elif self.vat_type == "flat":
            template = 'erpnextswiss/templates/xml/taxes_net.html'
        else:
            template = 'erpnextswiss/templates/xml/taxes_effective.html'
        content = frappe.render_template(template, data)
        return { 'content': content }

# sum of a column of a VAT query in the given period
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
