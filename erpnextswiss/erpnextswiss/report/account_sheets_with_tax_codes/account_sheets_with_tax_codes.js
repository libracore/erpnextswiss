// Copyright (c) 2017-2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Account Sheets with Tax Codes"] = {
    "filters": [
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("company") || frappe.defaults.get_global_default("company")
        },
        {
            "fieldname":"from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": (new Date(new Date().getFullYear(), 0, 1)), /* use first day of current year */
            "reqd": 1
        },
        {
            "fieldname":"to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname":"from_account",
            "label": __("From Account"),
            "fieldtype": "Int"
        },
        {
            "fieldname":"to_account",
            "label": __("To Account"),
            "fieldtype": "Int"
        },
        {
            "fieldname":"cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center"
        }
    ],
    "onload": (report) => {
        report.page.add_inner_button( __("CSV"), function () {
            download_csv(
                frappe.query_report.get_filter_value("company"),
                frappe.query_report.get_filter_value("from_date"),
                frappe.query_report.get_filter_value("to_date"),
                frappe.query_report.get_filter_value("from_account"),
                frappe.query_report.get_filter_value("to_account"),
                frappe.query_report.get_filter_value("cost_center")
            );
        });
    }
};

function download_csv(company, from_date, to_date, from_account, to_account, cost_center) {
    var url = "/api/method/erpnextswiss.erpnextswiss.report.account_sheets_with_tax_codes.account_sheets_with_tax_codes.get_csv"
        + "?company=" + encodeURIComponent(company)
        + "&from_date=" + encodeURIComponent(from_date) 
        + "&to_date=" + encodeURIComponent(to_date) 
        + "&from_account=" + encodeURIComponent(from_account || "") 
        + "&to_account=" + encodeURIComponent(to_account || "") 
        + "&cost_center=" + encodeURIComponent(cost_center || "");
    var w = window.open(
        frappe.urllib.get_full_url(url)
    );
    if (!w) {
        frappe.msgprint( __("Please enable pop-ups") );
    }
}
