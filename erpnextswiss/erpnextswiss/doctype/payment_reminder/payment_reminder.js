// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Reminder', {
    refresh: function(frm) {

    },
    on_submit: function(frm) {
        update_reminder_levels(frm);
    }
});

function update_reminder_levels(frm) {
    frappe.call({
		method: 'update_reminder_levels',
		doc: frm.doc,
		callback: function(response) {
		   // do nothing
		}
	});
}
