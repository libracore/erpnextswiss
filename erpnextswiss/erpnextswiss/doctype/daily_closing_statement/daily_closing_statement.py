# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DailyClosingStatement(Document):
    def validate(self):
        pass
        
    def before_save(self):
        # run this before saving
        self.collect_values()
        
    def collect_values(self):
        # get all sales in the selecte period
        sql_query = """SELECT `tabSales Invoice Item`.`item_code` AS `item`,
              `tabSales Invoice Item`.`parent` AS `sinv`,
              `tabSales Invoice Item`.`item_name` AS `item_name`,
              `tabSales Invoice Item`.`item_group` AS `item_group`,
              `tabSales Taxes and Charges`.`rate` AS `tax_rate`, 
              `tabSales Invoice Item`.`amount` AS `amount`,
              ROUND(IF(`tabSales Taxes and Charges`.`rate` IS NULL, 1, 1 + (`tabSales Taxes and Charges`.`rate` / 100)) * `tabSales Invoice Item`.`amount`, 2) AS `gross`
            FROM `tabSales Invoice Item`
            LEFT JOIN `tabSales Taxes and Charges` ON `tabSales Invoice Item`. `parent` = `tabSales Taxes and Charges`.`parent`
            LEFT JOIN `tabSales Invoice` ON `tabSales Invoice Item`.`parent` = `tabSales Invoice`.`name`
            WHERE `tabSales Invoice`.`posting_date` >= "{start_date}" AND `tabSales Invoice`.`posting_date` <= "{end_date}";
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        
        self.items = []
        for result in results:
            """self.items.append({
                'parent': self.name,
                'doctype': 'Daily Closing Statement Item',
                'parentfield': "items",
                'parenttype': "Daily Closing Statement",
                'item_code': result['item'],
                'sales_invoice': result['sinv'],
                'amount': result['gross']
            })"""
            row = self.append('items', {
                'item_code': result['item'], 
                'item_name': result['item_name'],
                'item_group': result['item_group'],
                'sales_invoice': result['sinv'], 
                'amount': result['gross']
            })
            
            
	pass
