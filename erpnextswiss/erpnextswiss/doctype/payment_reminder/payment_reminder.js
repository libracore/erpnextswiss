// Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Reminder', {
    refresh: function(frm) {

    },
    reminder_charge: function(frm) {
        update_total(frm);
    },
    total_before_charge: function(frm) {
        update_total(frm);
    }
});

function update_total(frm) {
    cur_frm.set_value("total_with_charge", ((frm.doc.total_before_charge || 0) + (frm.doc.reminder_charge || 0)));
}
