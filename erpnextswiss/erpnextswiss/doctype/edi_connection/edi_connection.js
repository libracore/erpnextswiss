// Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('EDI Connection', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Create File"), function() {
                create_file(frm);
            });
        }
    }
});

function create_file(frm) {
    frappe.call({
        'method': 'create_file',
        'doc': frm.doc,
        'callback': function(r) {
            cur_frm.reload_doc();
        }
     });
}
