# Copyright (c) 2016-2020, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    if not filters.from_date:
        filters.from_date = "2000-01-01"
    if not filters.end_date:
        filters.end_date = "2999-12-31"
    if not filters.code:
        filters.code = "200"
        
    column_defs = frappe.db.sql("""DESCRIBE `viewVAT_{code}`;""".format(
            code=filters.code), as_dict = True)
    columns = []
    for column in column_defs:
        columns.append(column['Field'])
        
    data = frappe.db.sql("""SELECT
            *
        FROM `viewVAT_{code}`
        WHERE
            `posting_date` >= \"{start_date}\"
            AND `posting_date` <= \"{end_date}\"
        ORDER BY
            `posting_date`;""".format(
            start_date=filters.from_date, end_date=filters.end_date, code=filters.code), as_list = True)
        
    return columns, data
