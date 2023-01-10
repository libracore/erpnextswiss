// Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
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
        }
    ],
    "initial_depth": 0
};

/* add event listener for double clicks to move up */
cur_page.container.addEventListener("dblclick", function(event) {
    // restrict to this report to prevent this event on other reports once loaded
    if (window.location.toString().includes("/Service%20Invoicing") ) {
        var row = event.delegatedTarget.getAttribute("data-row-index");
        var column = event.delegatedTarget.getAttribute("data-col-index");
        if (column.toString() === "10") {                 // 10 is the column index of "Create invoice"
            console.log("Create invoice for " + frappe.query_report.data[row]['customer']);
            frappe.call({
                'method': "erpnextswiss.erpnextswiss.report.service_invoicing.service_invoicing.create_invoice",
                'args': {
                    'from_date': frappe.query_report.filters[0].value,
                    'to_date': frappe.query_report.filters[1].value,
                    'customer': frappe.query_report.data[row]['customer'] 
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
