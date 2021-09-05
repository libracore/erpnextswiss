// Copyright (c) 2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Monthly Worktime"] = {
	"filters": [
        {
            "fieldname":"employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "reqd": 1,
            "options": "Employee"
        },
        {
            "fieldname":"month",
            "label": __("Month"),
            "fieldtype": "Int",
            "reqd": 1,
            "default": (new Date().getMonth() + 1)
        },
        {
            "fieldname":"year",
            "label": __("Year"),
            "fieldtype": "Int",
            "reqd": 1,
            "default": new Date().getFullYear()
        },
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default" : frappe.defaults.get_default("Company")
        }
	]
};
