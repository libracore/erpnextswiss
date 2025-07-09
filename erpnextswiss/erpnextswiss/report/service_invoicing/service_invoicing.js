// Copyright (c) 2022-2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Service Invoicing"] = {
    "filters": [
        {
            "fieldname":"from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": new Date().getFullYear() + "-01-01"
        },
        {
            "fieldname":"to_date",
            "label": __("To Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname":"customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        },
        {
            "fieldname":"group_by",
            "label": __("Customer"),
            "fieldtype": "Select",
            "options": "Customer\nProject",
            "default": "Customer",
            "reqd": 1
        },
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_global_default("company"),
            "reqd": 1
        }
    ],
    "initial_depth": 0
};

/* add event listener for double clicks to move up */
cur_page.container.addEventListener("dblclick", function(event) {
    // restrict to this report to prevent this event on other reports once loaded
    if (window.location.toString().includes("/Service%20Invoicing") ) {
        let row = event.delegatedTarget.getAttribute("data-row-index");
        let column = event.delegatedTarget.getAttribute("data-col-index");
        
        if (column.toString() === "10") {                 // 10 is the column index of "Create invoice"
            console.log("Create invoice for " + frappe.query_report.data[row]['customer']);
            let project = null;
            if (frappe.query_report.get_filter_value("group_by") === "Project") {
                project = frappe.query_report.data[row]['project'];
            }
            frappe.call({
                'method': "erpnextswiss.erpnextswiss.report.service_invoicing.service_invoicing.create_invoice",
                'args': {
                    'from_date': (frappe.query_report.get_filter_value("from_date") || "2000-01-01"),
                    'to_date': (frappe.query_report.get_filter_value("to_date") || "2099-12-31"),
                    'customer': frappe.query_report.data[row]['customer'],
                    'project': project
                },
                'callback': function(response) {
                    frappe.show_alert( __("Created") + ": <a href='/desk#Form/Sales Invoice/" + response.message
                        + "'>" + response.message + "</a>");
                    frappe.query_report.refresh();
                }
            });
        }
    }
});
