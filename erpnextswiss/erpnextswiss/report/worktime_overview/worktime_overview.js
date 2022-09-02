// Copyright (c) 2016, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.query_reports["Worktime Overview"] = {
    "filters": [
                {
                    "fieldname":"from_date",
                    "label": __("From date"),
                    "fieldtype": "Date",
                    "default": new Date().getFullYear() + "-01-01"
                },
                {
                    "fieldname":"to_date",
                    "label": __("To date"),
                    "fieldtype": "Date",
                    "default" : frappe.datetime.get_today()
                },
                {
                    "fieldname":"employee",
                    "label": __("Employee"),
                    "fieldtype": "Link",
                    "options": "Employee",
                    "hidden": frappe.user.has_role('HR Manager') ? 0 : 1,
                    "get_query": () => {
                        var company = frappe.query_report.get_filter_value('company');
                        return {
                            filters: {
                                'company': company
                            }
                        }
                    }
                },
                {
                    "fieldname":"company",
                    "label": __("Company"),
                    "fieldtype": "Link",
                    "options": "Company",
                    "reqd": 1,
                    "hidden": frappe.user.has_role('HR Manager') ? 0 : 1,
                    "on_change": () => {
                        frappe.query_report.set_filter_value('employee', "");
                        frappe.query_report.refresh();
                    }
                },
                {
                    "fieldname":"ignore_py",
                    "label": __("Ignore previous year"),
                    "fieldtype": "Check"
                }
            ],
    "onload": function() {
        return frappe.call({
            "method": "erpnextswiss.erpnextswiss.report.worktime_overview.worktime_overview.get_company",
            "args": {},
            "async": true,
            "callback": function(response) {
                var company = response.message;
                var company_filter = frappe.query_report.get_filter('company');
                company_filter.df.default = company;
                company_filter.refresh();
                company_filter.set_input(company_filter.df.default);
            }
        });
    }
}
