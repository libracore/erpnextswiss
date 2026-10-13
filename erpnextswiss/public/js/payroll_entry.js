// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payroll Entry", {
    refresh(frm) {
        if (frm.is_new() || frm.doc.docstatus !== 0 || !(frm.doc.employees || []).length) return;
        frm.add_custom_button(__("Check Quellensteuer"), () => {
            frappe.call({
                method: "erpnextswiss.erpnextswiss.quellensteuer.payroll.preflight",
                args: {payroll_entry: frm.doc.name},
                freeze: true,
                freeze_message: __("Checking Quellensteuer..."),
                callback: (response) => {
                    const issues = response.message || [];
                    frappe.msgprint({
                        title: __("Quellensteuer"),
                        indicator: issues.length ? "orange" : "green",
                        message: issues.length
                            ? issues.map((issue) => `<b>${frappe.utils.escape_html(issue.employee_name)}</b>: ${frappe.utils.escape_html(issue.issue)}`).join("<br>")
                            : __("Quellensteuer can be calculated for all {0} employees.", [frm.doc.employees.length])
                    });
                }
            });
        });
    }
});
