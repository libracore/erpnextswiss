# Copyright (c) 2013, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns, data = [], []

    # prepare columns
	columns = [
		"Customer:Link/Customer:200", 
		"Item Code:Link/Item:200", 
		"Item Name::200", 
		"Quantity::100", 
		"Amount:Currency:200"]

	# prepare filters
	if filters.customer:
		customer = filters.customer
	else:
		customer = "%"
	if filters.from_date:
		from_date = filters.from_date
	else:
		from_date = "2000-01-01"
	if filters.to_date:
		to_date = filters.to_date
	else:
		to_date = "2999-12-31"	

	# prepare query
	sql_query = """SELECT 
				  `t2`.`customer`,
				  `t1`.`item_code`, 
				  `t1`.`item_name`, 
				  SUM(`t1`.`qty`),
				  SUM(`t1`.`base_amount`)
				FROM `tabSales Invoice Item` AS `t1`
				LEFT JOIN `tabSales Invoice` AS `t2` ON `t1`.`parent` = `t2`.`name`
				WHERE 
				  `t2`.`docstatus` = 1
				  AND `t2`.`customer` LIKE '{customer}'
				  AND `t2`.`posting_date` >= '{from_date}'
				  AND `t2`.`posting_date` <= '{to_date}'
				GROUP BY `t2`.`customer`, `t1`.`item_code`
				ORDER BY `t1`.`item_code` ASC;""".format(customer=customer, from_date=from_date, to_date=to_date)

	# run query, as list, otherwise export to Excel fails 
	data = frappe.db.sql(sql_query, as_list = True)

	return columns, data
