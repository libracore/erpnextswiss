// Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pincode', {
    refresh: function(frm) {

    },
    validate: function(frm) {
        cur_frm.set_value('title', frm.doc.pincode + "-" + frm.doc.city);
    }
});
