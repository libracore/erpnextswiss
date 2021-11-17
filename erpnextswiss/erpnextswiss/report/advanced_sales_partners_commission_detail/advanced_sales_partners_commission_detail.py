# Copyright (c) 2013-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = [], []
    
    columns = ["Sales Partner:Link/Sales Partner:150", 
        "Sales Invoice:Link/Sales Invoice:150", 
        "Date:Date:100", 
        "Invoiced Amount (Exclusive Tax):Currency:210", 
        "Total Commission:Currency:150",
        "Average Commission Rate:Percent:170"]
    
    if not filters.from_date:
        filters.from_date = "2000-01-01"
    if not filters.end_date:
        filters.end_date = "2999-12-31"

    if filters.sales_partner:
        conditions = """ AND `tabSales Invoice`.`sales_partner` = "{0}" """.format(filters.sales_partner)
    else:
        conditions = ""
        
    data = frappe.db.sql("""SELECT
            `tabSales Invoice`.`sales_partner` as "Sales Partner:Link/Sales Partner:150",
            `tabSales Invoice`.`name` as "Sales Invoice:Link/Sales Invoice:150",
            `tabSales Invoice`.`posting_date` as "Date:Date:150",
            `tabSales Invoice`.`base_net_total` as "Invoiced Amount (Exculsive Tax):Currency:210",
            `tabSales Invoice`.`total_commission` as "Total Commission:Currency:150",
            100 * `tabSales Invoice`.`total_commission` / base_net_total as "Average Commission Rate:Currency:170"
        FROM `tabSales Invoice`
        LEFT JOIN `tabSales Partner` ON `tabSales Partner`.`name` = `tabSales Invoice`.`sales_partner`
        WHERE
            `tabSales Invoice`.`docstatus` = 1 
            AND `tabSales Invoice`.`posting_date` >= "{start_date}"
            AND `tabSales Invoice`.`posting_date` <= "{end_date}"
            AND IFNULL(`base_net_total`, 0) > 0 
            AND IFNULL(`total_commission`, 0) > 0
            {conditions}
        ORDER BY `tabSales Invoice`.`sales_partner` ASC, `tabSales Invoice`.`name` DESC
            ;""".format(
            start_date=filters.from_date, end_date=filters.end_date, conditions=conditions), as_list = True)

    return columns, data
