// Copyright (c) 2016-2020, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kontrolle MwSt"] = {
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
        },
        {
            "fieldname":"code",
            "label": __("Code"),
            "fieldtype": "Select",
            "options": "200\n220\n221\n225\n230\n235\n302\n312\n342\n382\n400\n405",
            "default" : "200",
            "reqd": 1
        }
	]
};
