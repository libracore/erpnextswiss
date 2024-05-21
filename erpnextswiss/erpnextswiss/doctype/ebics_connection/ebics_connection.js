// Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ebics Connection', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            if (frm.doc.activated) {
                cur_frm.dashboard.add_comment( __("This ebics connection is activated."), 'green', true);
            } else {
                frm.add_custom_button( __("Activation Wizard"), function() {
                    activation_wizard(frm);
                })
            }
        }
    }
});

function activation_wizard(frm) {
    frappe.call({
        'method': 'get_activation_wizard',
        'doc': frm.doc,
        'callback': function (response) {
            var d = new frappe.ui.Dialog({
                'fields': [
                    {'fieldname': 'ht', 'fieldtype': 'HTML'}
                ],
                primary_action: function(){
                    d.hide();
                    // depending on the stage, initiate next step
                    if (response.stage === 0) {
                        // do nothing, user needs to fill in the form
                    } else if (response.message.stage === 1) {
                        // create keys
                        frappe.call({
                            'method': 'create_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 2) {
                        // send signature
                        frappe.call({
                            'method': 'send_signature',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 3) {
                        // send keys
                        frappe.call({
                            'method': 'send_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 4) {
                        // create INI letter
                        frappe.call({
                            'method': 'create_ini_letter',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 5) {
                        // download public keys
                        frappe.call({
                            'method': 'download_public_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 6) {
                        // activate connection
                        frappe.call({
                            'method': 'activate_account',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else {
                        // do nothing, all set
                    }
                },
                primary_action_label: __('Next')
            });
            d.fields_dict.ht.$wrapper.html(response.message.html);
            d.show();
        }
    });
}
