// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on("QST Employee Record", {
    qst_records_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (frm.is_new() || (row.municipality && row.canton)) return;
        frappe.call({
            method: "erpnextswiss.erpnextswiss.quellensteuer.employee.location_from_address",
            args: {employee: frm.doc.name},
            callback: (response) => {
                const location = response.message || {};
                if (location.municipality && !row.municipality) {
                    frappe.model.set_value(cdt, cdn, "municipality", location.municipality);
                }
                if (location.canton && !row.canton) {
                    frappe.model.set_value(cdt, cdn, "canton", location.canton);
                }
            }
        });
    }
});
