// Copyright (c) 2020, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ZUGFeRD Wizard', {
	refresh: function(frm) {
        if (frm.doc.supplier_name) {
            frm.add_custom_button(__("Create invoice"), function() {
                frappe.show_alert( __("doing it...!") );
            });
        }
	},
    file: function(frm) {
        if (frm.doc.file) {
            frappe.call({
                method: 'read_file',
                doc: frm.doc,
                callback: function(response) {
                   var invoice = response.message;
                   cur_frm.set_value('supplier_name', invoice.supplier_name);
                }
            });
        } else {
            cur_frm.set_value('supplier_name', null);
        }
    }
});
