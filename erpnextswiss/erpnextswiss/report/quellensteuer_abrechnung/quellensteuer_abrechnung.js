// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.query_reports["Quellensteuer Abrechnung"] = {
    "filters": [
        {"fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company")},
        {"fieldname": "canton", "label": __("Canton"), "fieldtype": "Link", "options": "QST Canton"},
        {"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start()},
        {"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end()}
    ]
};
