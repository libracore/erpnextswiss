// Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Budget Control"] = {
    "filters": [
        {
            "fieldname":"date",
            "label": __("Date"),
            "fieldtype": "Date",
            "default": new Date(),
            "reqd": 1
        },
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("company"),
            "reqd": 1
}
    ]
};
