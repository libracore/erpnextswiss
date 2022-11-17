# Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 80},
        {"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": _("Barcode"), "fieldname": "barcode", "fieldtype": "Data", "width": 120},        
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 75},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Float", "precision": 2, "width": 75},
        {"label": _("Address"), "fieldname": "address", "fieldtype": "Link", "options": "Address", "width": 200}
    ]

def get_data(filters):
    # prepare query
    sql_query = """
        SELECT
            `tabEDI Sales Report`.`date` AS `date`,
            `tabEDI Sales Report Item`.`item_code` AS `item_code`,
            `tabEDI Sales Report Item`.`barcode` AS `barcode`,
            SUM(`tabEDI Sales Report Item`.`qty`) AS `qty`,
            SUM(`tabEDI Sales Report Item`.`qty` * `tabEDI Sales Report Item`.`rate`)  AS `amount`,
            `tabEDI Sales Report Item`.`address` AS `address`
        FROM `tabEDI Sales Report Item`
        LEFT JOIN `tabEDI Sales Report` ON `tabEDI Sales Report`.`name` = `tabEDI Sales Report Item`.`parent`
        WHERE 
            `tabEDI Sales Report`.`date` >= "{from_date}"
            AND `tabEDI Sales Report`.`date` <= "{to_date}"
        GROUP BY CONCAT(`tabEDI Sales Report Item`.`barcode`, "-", 
            IFNULL(`tabEDI Sales Report Item`.`address`, "-"), "-",
            `tabEDI Sales Report`.`date`)
        ORDER BY `tabEDI Sales Report`.`date` ASC, `tabEDI Sales Report Item`.`item_code` ASC
      """.format(from_date=filters.from_date, to_date=filters.to_date)
    
    data = frappe.db.sql(sql_query, as_dict=1)

    return data
