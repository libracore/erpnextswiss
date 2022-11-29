// Copyright (c) 2016, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kontrolle MwSt DE"] = {
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
            "options": "81\n86\n35\n77\n76\n41\n44\n49\n43\n48\n89\n93\n95\n94\n91\n46\n73\n84\n42\n60\n21\n45\n66\n61\n62\n67\n63\n59\n64\n65\n69",
            "default" : "81",
            "reqd": 1
        },
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default" : frappe.defaults.get_default("Company"),
            "reqd": 1
        }
    ]
};
