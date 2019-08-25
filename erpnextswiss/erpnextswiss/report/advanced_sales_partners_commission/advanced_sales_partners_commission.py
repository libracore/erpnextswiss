# Copyright (c) 2013-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    columns = ["Sales Partner:Link/Sales Partner:150", 
        "Invoiced Amount (Exclusive Tax):Currency:210", 
        "Total Commission:Currency:150",
        "Average Commission Rate:Percent:170"]
    
    if not filters.from_date:
        filters.from_date = "2000-01-01"
    if not filters.end_date:
        filters.end_date = "2999-12-31"
        
    data = frappe.db.sql("""SELECT
            `sales_partner` AS \"Sales Partner:Link/Sales Partner:150\",
            SUM(`base_net_total`) AS \"Invoiced Amount (Exclusive Tax):Currency:210\",
            SUM(`total_commission`) AS \"Total Commission:Currency:150\",
            SUM(`total_commission`)*100/SUM(`base_net_total`) AS \"Average Commission Rate:Percent:170\"
        FROM `tabSales Invoice`
        WHERE
            `docstatus` = 1 
            AND `posting_date` >= \"{start_date}\"
            AND `posting_date` <= \"{end_date}\"
            AND IFNULL(`base_net_total`, 0) > 0 
            AND IFNULL(`total_commission`, 0) > 0
        GROUP BY
            `sales_partner`
        ORDER BY
            \"Total Commission:Currency:120\"""".format(
            start_date=filters.from_date, end_date=filters.end_date), as_list = True)

    return columns, data

