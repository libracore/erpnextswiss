// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee", {
    qst_records_add(frm, cdt, cdn) {
        if (frm.is_new() || locals[cdt][cdn].municipality) return;
        frappe.call({
            method: "erpnextswiss.erpnextswiss.quellensteuer.employee.municipality_from_address",
            args: {employee: frm.doc.name},
            callback: (response) => {
                if (response.message) {
                    frappe.model.set_value(cdt, cdn, "municipality", response.message);
                }
            }
        });
    }
});
