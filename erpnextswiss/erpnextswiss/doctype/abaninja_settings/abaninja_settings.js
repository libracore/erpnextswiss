// Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on("AbaNinja Settings", {
    refresh(frm) {
        frm.add_custom_button(__('Sync customers'), function () {
            frappe.dom.freeze(__('Fetching customer records from AbaNinja, please wait...'));
            frappe.call({
                'method': 'erpnextswiss.erpnextswiss.abaninja.sync_abaninja_customers',
                'callback': function (response) {
                    frappe.dom.unfreeze();
                    if (response.message) {
                        let res = response.message;

                        if (res.success === false) {
                            frappe.msgprint({
                                title: __('Sync Failed'),
                                indicator: 'red',
                                message: `<p class="text-danger">${res.message}</p>`
                            });
                            return;
                        }

                        frappe.msgprint({
                            title: __('Sync Completed'),
                            indicator: 'green',
                            message: `
                                <p>${res.message}</p>
                                <hr>
                                <ul>
                                    <li><b>Profiles Inserted:</b> ${res.inserted}</li>
                                    <li><b>Profiles Updated:</b> ${res.updated}</li>
                                </ul>
                            `
                        });
                    }
                },
                'error': function (response) {
                    frappe.dom.unfreeze();
                    frappe.msgprint({
                        title: __('Critical Error'),
                        indicator: 'red',
                        message: __('Could not establish connection to server.')
                    });
                }
            });
        }).addClass('btn-primary');
    },
});
