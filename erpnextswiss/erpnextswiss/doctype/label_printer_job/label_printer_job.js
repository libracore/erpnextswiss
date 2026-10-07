// Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Label Printer Job', {
    refresh: function(frm) {
        if(frm.doc.status == "Failed") {
            frm.add_custom_button(__("Retry"), function() {
                retry_printing(frm);
            });
        }
    }
});


function retry_printing(frm) {
    frm.set_value("status","Waiting");
    frm.save().then(() => {
        frm.reload_doc();
    })
}