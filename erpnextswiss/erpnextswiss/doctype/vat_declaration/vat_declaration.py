# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class VATDeclaration(Document):
	pass

@frappe.whitelist()
def get_revenue(start_date, end_date):
    revenue = frappe.db.sql("SELECT SUM(`base_grand_total`) AS `total_revenue` " +
        "FROM `tabSales Invoice` " +
        "WHERE `posting_date` >= '{0}' AND `posting_date` <= '{1}' AND `docstatus` = 1".format(
            start_date, end_date)
        , as_dict=True)
        
    return { 'total_revenue': revenue.total_revenue }
