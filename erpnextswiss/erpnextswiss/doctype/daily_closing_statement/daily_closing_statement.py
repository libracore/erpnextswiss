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
              ROUND(IF(`tabSales Taxes and Charges`.`rate` IS NULL, 1, 1 + (`tabSales Taxes and Charges`.`rate` / 100)) * `tabSales Invoice Item`.`amount`, 5) AS `gross`
            FROM `tabSales Invoice Item`
            LEFT JOIN `tabSales Taxes and Charges` ON `tabSales Invoice Item`. `parent` = `tabSales Taxes and Charges`.`parent`
            LEFT JOIN `tabSales Invoice` ON `tabSales Invoice Item`.`parent` = `tabSales Invoice`.`name`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND `tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}";
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        
        self.items = []
        for result in results:
            row = self.append('items', {
                'item_code': result['item'], 
                'item_name': result['item_name'],
                'item_group': result['item_group'],
                'sales_invoice': result['sinv'], 
                'amount': result['gross']
            })
        
        # total sales
        sql_query = """SELECT SUM(`tabSales Invoice`.`base_grand_total`) AS `base_grand_total`
            FROM `tabSales Invoice`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND `tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}";
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        self.total_sales = results[0]['base_grand_total']
        # number of customers 
        sql_query = """SELECT COUNT(`tabSales Invoice`.`customer`) AS `customer_count`
            FROM `tabSales Invoice`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND`tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}
            GROUP BY `tabSales Invoice`.`customer`";
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        self.number_of_customers = results[0]['customer_count']        
        # average & highest sales
        sql_query = """SELECT AVG(`tabSales Invoice`.`base_grand_total`) AS `avg`,
              MAX(`tabSales Invoice`.`base_grand_total`) AS `max`
            FROM `tabSales Invoice`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND`tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}";
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        self.average_sales = results[0]['avg']
        self.highest_sale = results[0]['max']
        # discounts
        sql_query = """SELECT SUM(`tabSales Invoice`.`base_discount_amount`) AS `discounts`
            FROM `tabSales Invoice`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND`tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}
            GROUP BY `tabSales Invoice`.`customer`";
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        self.discounts = results[0]['discounts']  
        
        # by groups
        sql_query = """SELECT 
              COUNT(`tabSales Invoice Item`.`item_code`) AS `count`,
              `tabSales Invoice Item`.`item_group` AS `item_group`,
              `tabSales Taxes and Charges`.`rate` AS `tax_rate`, 
              SUM(`tabSales Invoice Item`.`amount`) AS `amount`,
              SUM(ROUND(IF(`tabSales Taxes and Charges`.`rate` IS NULL, 1, 1 + (`tabSales Taxes and Charges`.`rate` / 100)) * `tabSales Invoice Item`.`amount`, 5)) AS `gross`
            FROM `tabSales Invoice Item`
            LEFT JOIN `tabSales Taxes and Charges` ON `tabSales Invoice Item`. `parent` = `tabSales Taxes and Charges`.`parent`
            LEFT JOIN `tabSales Invoice` ON `tabSales Invoice Item`.`parent` = `tabSales Invoice`.`name`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND`tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}"
            GROUP BY `tabSales Invoice Item`.`item_group`;
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        
        self.groups = []
        for result in results:
            row = self.append('groups', {
                'item_group': result['item_group'],
                'count': result['count'], 
                'amount': result['gross']
            })
            
        # by currency
        sql_query = """SELECT 
              COUNT(`tabSales Invoice`.`name`) AS `count`,
              `tabSales Invoice`.`currency` AS `currency`,
              SUM(`tabSales Invoice`.`base_grand_total`) AS `amount`
            FROM `tabSales Invoice`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND`tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}"
            GROUP BY `tabSales Invoice`.`currency`;
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        
        self.currencies = []
        for result in results:
            row = self.append('currencies', {
                'currency': result['currency'],
                'count': result['count'], 
                'amount': result['amount']
            })
            
        # by payment mode
        sql_query = """SELECT 
              COUNT(`tabSales Invoice Payment`.`name`) AS `count`,
              `tabSales Invoice Payment`.`mode_of_payment` AS `mode_of_payment`,
              SUM(`tabSales Invoice Payment`.`base_amount`) AS `amount`
            FROM `tabSales Invoice Payment`
            LEFT JOIN `tabSales Invoice` ON `tabSales Invoice Payment`.`parent` = `tabSales Invoice`.`name`
            WHERE 
              `tabSales Invoice`.`docstatus` = 1
              AND`tabSales Invoice`.`posting_date` >= "{start_date}" 
              AND `tabSales Invoice`.`posting_date` <= "{end_date}"
            GROUP BY `tabSales Invoice Payment`.`mode_of_payment`;
        """.format(start_date=self.start_date, end_date=self.end_date)
        results = frappe.db.sql(sql_query, as_dict=True)
        
        self.payment_modes = []
        for result in results:
            row = self.append('payment_modes', {
                'mode_of_payment': result['mode_of_payment'],
                'count': result['count'], 
                'amount': result['amount']
            })
	pass
