// Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pincode', {
    refresh: function(frm) {
        frm.add_custom_button( __("Open Map") , function() {
            frappe.call({
                "method": "erpnextswiss.erpnextswiss.swisstopo.get_swisstopo_url_from_pincode",
                "args": {
                    "pincode": frm.doc.pincode,
                    "language": "de",
                    "zoom": 8
                },
                "callback": function(response) {
                    var url = response.message;
                    window.open(url, '_blank');
                }
            });
        });
    },
    validate: function(frm) {
        cur_frm.set_value('title', frm.doc.pincode + "-" + frm.doc.city);
    }
});
