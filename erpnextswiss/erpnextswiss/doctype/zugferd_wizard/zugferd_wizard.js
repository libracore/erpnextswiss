// Copyright (c) 2019-2023, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

const clear_message = __("Please load a file...");

frappe.ui.form.on('ZUGFeRD Wizard', {
    refresh: function(frm) {
        // set company if empty
        if (!frm.doc.company) {
            cur_frm.set_value("company", frappe.defaults.get_user_default("company") || frappe.defaults.get_global_default("company"));
        }
        
        // filters
        cur_frm.fields_dict['default_item'].get_query = function(doc) {
             return {
                 filters: {
                     "is_purchase_item": 1,
                     "disabled": 0
                 }
             }
        }
        cur_frm.fields_dict['default_tax'].get_query = function(doc) {
             return {
                 filters: {
                     "company": frm.doc.company
                 }
             }
        }

        if (frm.doc.ready_for_import) {
            frm.add_custom_button(__("Create invoice"), function() {
                frappe.call({
                    'method': 'create_invoice',
                    'doc': frm.doc,
                    'freeze': true,
                    'freeze_message': __("Creating invoice..."),
                    'callback': function(r) {
                        if (r.message.url) {
                            window.open(r.message.url, '_blank');
                            cur_frm.set_df_property('preview_html', 'options', clear_message);
                            cur_frm.reload_doc();
                        }
                    }
                })
            });
        } else if (cur_frm.attachments.get_attachments().length > 0) {
            frm.add_custom_button(__("Manually create invoice"), function() {
                create_manual_invoice(frm);
            });
        }
        if (frm.doc.content_dict) {
            frappe.call({
                'method': 'render_invoice',
                'doc': frm.doc,
                'args': {
                    'invoice': frm.doc.content_dict
                },
                'callback': function(response) {
                    var content = response.message;
                    cur_frm.set_df_property('preview_html', 'options', content.html);
                }
            })
        }
        
        if (!frm.doc.default_tax) {
            set_tax(frm)
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
                    'freeze': true,
                    'freeze_message': __("Reading invoice..."),
                    'callback': function(response) {
                        var content = response.message;
                        cur_frm.set_df_property('preview_html', 'options', content.html);
                        console.log(content.dict);
                        if (content.dict !== null) {
                            cur_frm.set_value('content_dict', JSON.stringify(content.dict));
                            cur_frm.set_value('ready_for_import', 1);
                            cur_frm.save();
                        } else {
                            cur_frm.set_value('ready_for_import', 0);
                            frappe.msgprint( __("This invoice cannot be interpreted automatically."), __("Information") );
                        }
                    }
                });
            }, 1000);
            
        } else {
            // no file --> clear
            cur_frm.set_df_property('preview_html', 'options', clear_message );
            cur_frm.set_value('content_dict', null);
            cur_frm.set_value('ready_for_import', 0);
        }
        
    },
    // change trigger on company
    company: function(frm) {
        if (frm.doc.company) {
            set_tax(frm);
        }
    }
});

function set_tax(frm) {
    frappe.call({
        'method': "frappe.client.get_list",
        'args': {
            'doctype': "Purchase Taxes and Charges Template",
            'filters': {
                'is_default': 1,
                'company': frm.doc.company
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

function create_manual_invoice(frm) {
    var d = new frappe.ui.Dialog({
        'title': __('Manually create invoice'),
        'fields': [
            {
                'fieldname': 'company', 
                'fieldtype': 'Link', 
                'label': __('Company'), 
                'reqd': 1, 
                'options': 'Company',
                'default': frm.doc.company,
                'onchange': function() {
                    frappe.call({
                        'method': "frappe.client.get",
                        'args': {
                            'doctype': "Company",
                            'name': d.fields_dict.company.value
                        },
                        'callback': function(response) {
                            var company = response.message;
                            d.set_value("cost_center", company.cost_center)
                        }
                    });
                }
            },
            {
                'fieldname': 'supplier', 
                'fieldtype': 'Link', 
                'label': __('Supplier'), 
                'options': 'Supplier',
                'reqd': 1,
                'onchange': function() {
                    frappe.call({
                        'method': "frappe.client.get",
                        'args': {
                            'doctype': "Supplier",
                            'name': d.fields_dict.supplier.value
                        },
                        'callback': function(response) {
                            var supplier = response.message;
                            d.set_value("supplier_name", supplier.supplier_name);
                            d.set_value("payment_method", supplier.default_payment_method);
                            if (supplier.default_payment_method == "ESR") {
                                d.set_df_property('esr_code', 'hidden', 0);
                                d.set_df_property('esr_code', 'reqd', 1);
                            } else {
                                d.set_df_property('esr_code', 'hidden', 1);
                                d.set_df_property('esr_code', 'reqd', 0);
                                d.set_value("esr_code", "");
                            }
                        }
                    });
                }
            },
            {
                'fieldname': 'supplier_name', 
                'fieldtype': 'Data', 
                'label': __('Supplier name'), 
                'read_only': 1
            },
            {
                'fieldname': 'date', 
                'fieldtype': 'Date', 
                'label': __('Posting Date'), 
                'reqd': 1, 
                'default': frappe.datetime.get_today()
            },
            {
                'fieldname': 'project', 
                'fieldtype': 'Link', 
                'label': __('Project'), 
                'options': 'Project'
            },
            {
                'fieldname': 'bill_no', 
                'fieldtype': 'Data', 
                'label': __('Bill No'), 
                'reqd': 1
            },
            {
                'fieldname': 'item', 
                'fieldtype': 'Link', 
                'label': __('Item'), 
                'reqd': 1, 
                'options': 'Item',
                'default': frm.doc.default_item,
                'get_query': function() { return { filters: {'is_purchase_item': 1 } } }
            },
            {
                'fieldname': 'amount', 
                'fieldtype': 'Currency', 
                'label': __('Amount'), 
                'reqd': 1
            },
            {
                'fieldname': 'cost_center', 
                'fieldtype': 'Link', 
                'label': __('Cost Center'), 
                'reqd': 1, 
                'options': 'Cost Center',
                'get_query': function() { return { filters: {'company': d.fields_dict.company.value } } }
            },
            {
                'fieldname': 'taxes_and_charges', 
                'fieldtype': 'Link', 
                'label': __('Taxes and Charges Template'), 
                'reqd': 1, 
                'default': frm.doc.default_tax,
                'options': 'Purchase Taxes and Charges Template'
            },
            {
                'fieldname': 'remarks', 
                'fieldtype': 'Data', 
                'label': __('Remarks')
            },
            {
                'fieldname': 'esr_code', 
                'fieldtype': 'Data', 
                'label': __('ESR Code'),
                'hidden': 1,
                'reqd': 0
            },
            {
                'fieldname': 'payment_method', 
                'fieldtype': 'Data', 
                'label': __('Payment Method'),
                'hidden': 1
            }
        ],
        'primary_action': function() {
            d.hide();
            var values = d.get_values();
            frappe.call({
                    'method': "manual_purchase_invoice",
                    'doc': frm.doc,
                    'args':{
                        'company': values.company,
                        'supplier': values.supplier,
                        'date': values.date,
                        'project': values.project,
                        'bill_no': values.bill_no,
                        'item': values.item,
                        'amount': values.amount,
                        'cost_center': values.cost_center,
                        'taxes_and_charges': values.taxes_and_charges,
                        'remarks': values.remarks,
                        'esr_code': values.esr_code,
                        'payment_method': values.payment_method
                    },
                    'callback': function(r)
                    {
                        if (r.message.url) {
                            window.open(r.message.url, '_blank');
                            cur_frm.set_df_property('preview_html', 'options', clear_message);
                            cur_frm.reload_doc();
                        }
                    }
            });
        },
        'primary_action_label': __('Create')
    });
    d.show();
}
