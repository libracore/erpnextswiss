// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on("QST Tariff Import", {
    refresh(frm) {
        if (!frm.is_new() && ["Pending", "Failed"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Import"), () => {
                frappe.call({
                    method: "erpnextswiss.erpnextswiss.quellensteuer.tariff.start_import",
                    args: {name: frm.doc.name},
                    callback: () => frm.reload_doc()
                });
            });
        }
    }
});
