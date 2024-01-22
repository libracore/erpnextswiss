// Copyright (c) 2023, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Worldline TIM', {
    refresh: function(frm) {
        frm.add_custom_button(__("Show Test Site"), function() {
            frappe.set_route("worldline-tim-test");
        });
    }
});
