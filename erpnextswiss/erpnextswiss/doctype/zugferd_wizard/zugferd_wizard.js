// Copyright (c) 2019-2023, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ZUGFeRD Wizard', {
    refresh: function(frm) {
        // filter for crono based on customer link field
        cur_frm.fields_dict['default_item'].get_query = function(doc) {
             return {
                 filters: {
                     "is_purchase_item": 1,
                     "disabled": 0
                 }
             }
        }
        // set company if empty
        if (!frm.doc.company) {
            cur_frm.set_value("company", frappe.defaults.get_user_default("company") || frappe.defaults.get_global_default("company"));
        }
        
        if (frm.doc.ready_for_import) {
            frm.add_custom_button(__("Create invoice"), function() {
                frappe.call({
                    'method': 'create_invoice',
                    'doc': frm.doc,
                    'freeze': true,
                    'freeze_message': __("Creating invoice..."),
                    'callback': function() {
                        cur_frm.reload_doc();
                    }
                })
            });
        }
        if (!frm.doc.default_tax) {
            frappe.call({
                'method': "frappe.client.get_list",
                'args': {
                    'doctype': "Purchase Taxes and Charges Template",
                    'filters': {
                        'is_default': 1
                    },
                    'fields': ["name"]
                },
                'callback': function(response) {
                    var templates = response.message;
                    if (templates.length > 0) {
                       cur_frm.set_value("default_tax", templates[0]['name']);
                    }
                }
            });
        }
        if (!frm.doc.default_item) {
            frappe.call({
                'method': 'get_default_item',
                'doc': frm.doc,
                'callback': function(response) {
                   var default_item = response.message;
                   cur_frm.set_value("default_item", default_item);
                }
            });
        }
    },
    // change trigger on the file
    file: function(frm) {
        if (frm.doc.file) {
            // has a file --> read & interpret (prevent race condition with file save)
            setTimeout(function() {
                frappe.call({
                    'method': 'read_file',
                    'doc': frm.doc,
                    'callback': function(response) {
                       var content = response.message;
                       cur_frm.set_df_property('preview_html', 'options', content.html);
                       console.log(content.dict);
                       cur_frm.set_value('content_dict', JSON.stringify(content.dict));
                       cur_frm.set_value('ready_for_import', 1);
                       cur_frm.save();
                    }
                });
            }, 1000);
            
        } else {
            // no file --> clear
            cur_frm.set_df_property('preview_html', 'options', __("Please load a file...") );
            cur_frm.set_value('content_dict', null);
            cur_frm.set_value('ready_for_import', 0);
        }
        
    }
});
