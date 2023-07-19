# Copyright (c) 2016-2022, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns, data = [], []
    
    if not filters.from_date:
        filters.from_date = "2000-01-01"
    if not filters.end_date:
        filters.end_date = "2999-12-31"
    if not filters.code:
        filters.code = "200"

    # define columns
    columns = [
        {"label": _("Document"), "fieldname": "name", "fieldtype": "Dynamic Link", "options": "doctype", "width": 120},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Total"), "fieldname": "base_grand_total", "fieldtype": "Currency", "width": 100},
        {"label": _("Taxes and Charges"), "fieldname": "taxes_and_charges", "fieldtype": "Data", "width": 150},
        {"label": _("Tax Amount"), "fieldname": "total_taxes_and_charges", "fieldtype": "Currency", "width": 100},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 150}
    ]

    data = get_data(filters.from_date, filters.end_date, filters.code, filters.company)
    return columns, data

def get_data(from_date, end_date, code, company="%"):
    # try to fetch data from VAT query
    if frappe.db.exists("VAT query", "viewVAT_{code}".format(code=code)):
        sql_query = ("""SELECT * 
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
                query=frappe.get_value("VAT query", "viewVAT_{code}".format(code=code), "query"),
                start_date=from_date, end_date=end_date).replace("{company}", company))      
    else:
        # fallback database view
        sql_query = """SELECT
                    *
                FROM `viewVAT_{code}`
                WHERE
                    `posting_date` >= \"{start_date}\"
                    AND `posting_date` <= \"{end_date}\"
                ORDER BY
                    `posting_date`;""".format(
                    start_date=from_date, end_date=end_date, code=code)     
    try:
        data = frappe.db.sql(sql_query, as_dict = True)
    except:
        return []
    return data
