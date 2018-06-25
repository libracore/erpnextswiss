// Copyright (c) 2016, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Revenue per Item Group"] = {
	"filters": [
        {
            "fieldname":"from_date",
            "label": __("From date"),
            "fieldtype": "Date"
        },
        {
            "fieldname":"end_date",
            "label": __("End date"),
            "fieldtype": "Date",
            "default" : frappe.datetime.get_today()
        }
	]
}
