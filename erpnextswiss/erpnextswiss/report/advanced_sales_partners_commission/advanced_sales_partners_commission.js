// Copyright (c) 2016-2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Advanced Sales Partners Commission"] = {
	"filters": [
        {
            "fieldname":"from_date",
            "label": __("From date"),
            "fieldtype": "Date",
            "default": new Date().getFullYear() + "-01-01"
        },
        {
            "fieldname":"end_date",
            "label": __("End date"),
            "fieldtype": "Date",
            "default" : frappe.datetime.get_today()
        }
	]
}
