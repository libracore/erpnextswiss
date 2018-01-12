# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _

@frappe.whitelist()
def get_open_sales_invoices():
    # get unpaid sales invoices
    sql_query = ("SELECT `name`, `customer`, `base_grand_total`, `due_date` " +
                "FROM `tabSales Invoice` " +
                "WHERE `docstatus` = 1 " + 
                "AND `grand_total` = {0} ".format(amount) + 
                "AND `status` != 'Paid'")
    unpaid_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    return {'unpaid_sales_invoices': unpaid_sales_invoices }
