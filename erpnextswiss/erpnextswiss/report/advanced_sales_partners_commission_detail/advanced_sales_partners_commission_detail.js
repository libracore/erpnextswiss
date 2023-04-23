// Copyright (c) 2016-2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Advanced Sales Partners Commission Detail"] = {
    "filters": [
        {
            "fieldname":"sales_partner",
            "label": __("Sales Partner"),
            "fieldtype": "Link",
            "options": "Sales Partner"
        },
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
};
