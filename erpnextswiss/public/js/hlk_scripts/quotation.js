frappe.ui.form.on('Quotation', {
    validate(frm) {
        // Diese Funktion prüft ob zum entsprechenden Dokument bereits ein BG-Job läuft und wenn ja blockiert Sie das Speichern oder weitere BG-Jobs.
        frappe.call({
        'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_any_job_running",
            'args': {
                'doctype': "Quotation",
                'docname': cur_frm.doc.name
            },
            'callback': function(res) {
                var running_job = res.message;
                if (running_job) {
                    frappe.msgprint("Bitte warten Sie bis alle Hintergrundprozesse zu diesem Dokument abgeschlossen sind.");
                    frappe.validated=false;
                } else {
                    calc_valid_to_date(frm);
                    validate_hlk_element_allocation(frm);
                }
            }
        });
    },
    refresh(frm) {
        frappe.call({
            "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.get_item_group_for_structur_element_filter",
            "async": false,
            "callback": function(response) {
                var item_group_for_structur_element_filter = response.message;
                frm.fields_dict['hlk_structur_organisation'].grid.get_field('main_element').get_query = function(doc, cdt, cdn) {
                    return {    
                        filters:[
                            ['item_group', '=', item_group_for_structur_element_filter]
                        ]
                    }
                };
                
                frm.fields_dict['hlk_structur_organisation'].grid.get_field('parent_element').get_query = function(doc, cdt, cdn) {
                    return {    
                        filters:[
                            ['item_group', '=', item_group_for_structur_element_filter]
                        ]
                    }
                };
                
                frm.fields_dict['items'].grid.get_field('hlk_element').get_query = function(doc, cdt, cdn) {
                    return {    
                        filters:[
                            ['item_group', '=', item_group_for_structur_element_filter]
                        ]
                    }
                };
            }
        });
        
        cur_frm.fields_dict['introduction_template'].get_query = function(doc) {
             return {
                 filters: {
                     "quotation": 1,
                     "introduction": 1
                 }
             }
        };
        
        cur_frm.fields_dict['closing_text_template'].get_query = function(doc) {
             return {
                 filters: {
                     "quotation": 1,
                     "closing_text": 1
                 }
             }
        };
        
        if (!frm.doc.__islocal && cur_frm.doc.docstatus != '1') {
            if (!cur_frm.custom_buttons[__("Change Customer without impact on price")]) {
                frm.add_custom_button(__("Change Customer without impact on price"), function() {
                    change_customer(frm);
                });
            }
            if (!cur_frm.custom_buttons[__("Transfer HLK Discounts")]) {
                frm.add_custom_button(__("Transfer HLK Discounts"), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint(__("Please save Document first"));
                    } else {
                        transfer_structur_organisation_discounts(frm);
                    }
                }, __("HLK Tools"));
            }
            if (!cur_frm.custom_buttons[__("Calc HLK Totals")]) {
                frm.add_custom_button(__("Calc HLK Totals"), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint(__("Please save Document first"));
                    } else {
                        calc_structur_organisation_totals(frm);
                    }
                }, __("HLK Tools"));
            }
            if (!cur_frm.custom_buttons[__("Transfer Special Discounts")]) {
                frm.add_custom_button(__("Transfer Special Discounts"), function() {
                    if (cur_frm.is_dirty()) {
                        frappe.msgprint(__("Please save Document first"));
                    } else {
                        transfer_special_discounts(frm);
                    }
                }, __("HLK Tools"));
            }
        }
    },
    hlk_structur_organisation_template: function(frm) {
        if (cur_frm.doc.hlk_structur_organisation_template) {
            if (cur_frm.doc.hlk_structur_organisation.length < 1) {
                frappe.call({
                    "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.fetch_hlk_structur_organisation_table",
                    "args": {
                        'template': cur_frm.doc.hlk_structur_organisation_template
                    },
                    "async": false,
                    "callback": function(response) {
                        if (response.message) {
                            update_hlk_structur_organisation_rows(frm, response.message);
                        }
                    }
                });
            } else {
                cur_frm.set_value('hlk_structur_organisation_template', '');
                frappe.msgprint(__("Please remove table HLK Structur Organisation first"));
            }
        }
    }
})

function transfer_special_discounts(frm) {
    // Diese Funktion prüft ob zum entsprechenden Dokument bereits ein BG-Job läuft und wenn ja blockiert Sie das Speichern oder weitere BG-Jobs.
    frappe.call({
    'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_any_job_running",
        'args': {
            'doctype': "Quotation",
            'docname': cur_frm.doc.name
        },
        'callback': function(res) {
            var running_job = res.message;
            if (running_job) {
                frappe.msgprint("Bitte warten Sie bis alle Hintergrundprozesse zu diesem Dokument abgeschlossen sind.");
            } else {
                // Das ist die eigentliche Funktion
                if (cur_frm.doc.special_discounts) {
                    var discounts = cur_frm.doc.special_discounts;
                    var total_discounts = 0;
                    discounts.forEach(function(entry) {
                        if (entry.discount_type == 'Percentage') {
                            var percentage_amount = 0;
                            if (entry.is_cumulative) {
                                percentage_amount = (((cur_frm.doc.total - total_discounts) / 100) * entry.percentage);
                            } else {
                                percentage_amount = ((cur_frm.doc.total / 100) * entry.percentage);
                            }
                            total_discounts += percentage_amount;
                            entry.discount = percentage_amount;
                        } else {
                            total_discounts += entry.discount;
                        }
                    });
                    cur_frm.set_value('apply_discount_on', 'Net Total');
                    cur_frm.set_value('discount_amount', total_discounts);
                }
            }
        }
    });
}

function update_hlk_structur_organisation_rows(frm, data) {
    for (var i = 0; i < data.length; i++) {
        var child = cur_frm.add_child('hlk_structur_organisation');
        var entry = data[i];
        for (var key in entry) {
            if ((key !== 'name') && (key !== 'idx') && (key !== 'creation') && (key !== 'docstatus') && (key !== 'doctype') && (key !== 'modified') && (key !== 'modified_by') && (key !== 'owner') && (key !== 'parent') && (key !== 'parentfield') && (key !== 'parenttype')) {
                frappe.model.set_value(child.doctype, child.name, key, entry[key]);
            }
        }
        cur_frm.refresh_field('hlk_structur_organisation');
    }
}

function validate_hlk_element_allocation(frm) {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.validate_hlk_element_allocation",
        "async": false,
        "callback": function(response) {
            if (response.message == 'validate') {
                var hlk_element_allocation = check_hlk_element_allocation(frm);
                if (hlk_element_allocation != '') {
                    frappe.msgprint( __("Zuweisungen Strukturelemente unvollständig, prüfen Sie folgende Artikelpositionen:") + hlk_element_allocation, __("Validation") );
                    frappe.validated=false;
                }
            }
        }
    });
}

function calc_structur_organisation_totals(frm) {
    // Diese Funktion prüft ob zum entsprechenden Dokument bereits ein BG-Job läuft und wenn ja blockiert Sie das Speichern oder weitere BG-Jobs.
    frappe.call({
    'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_any_job_running",
        'args': {
            'doctype': "Quotation",
            'docname': cur_frm.doc.name
        },
        'callback': function(res) {
            var running_job = res.message;
            if (running_job) {
                frappe.msgprint("Bitte warten Sie bis alle Hintergrundprozesse zu diesem Dokument abgeschlossen sind.");
            } else {
                // Das ist die eigentliche Funktion
                if (!frm.doc.__islocal) {
                    var hlk_structur_without_parent = check_hlk_structur_allocation(frm);
                    if (hlk_structur_without_parent != '') {
                        frappe.confirm(
                            'Nachfolgende HLK Strukturen besitzen kein Eltern Element:' + hlk_structur_without_parent + '<br><br>Ist das korrekt und wollen Sie weiterfahren?',
                            function(){
                                // on yes
                                sub_calc_structur_organisation_totals(frm)
                            },
                            function(){
                                // on no
                                show_alert('Totalen Berechnung abgebrochen')
                            }
                        )
                    } else {
                        sub_calc_structur_organisation_totals(frm)
                    }
                }
            }
        }
    });
}
function sub_calc_structur_organisation_totals(frm) {
    frappe.dom.freeze(__("Calc HLK Totals..."));
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.calc_structur_organisation_totals",
        "args": {
            "dt": "Quotation",
            "dn": frm.doc.name
        },
        "async": false,
        "callback": function(response) {
            var jobname = response.message;
            if (jobname) {
                let calc_refresher = setInterval(calc_refresher_handler, 3000, jobname);
                function calc_refresher_handler(jobname) {
                    frappe.call({
                    'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_calc_job_running",
                        'args': {
                            'jobname': jobname
                        },
                        'callback': function(res) {
                            if (res.message == 'refresh') {
                                clearInterval(calc_refresher);
                                frappe.dom.unfreeze();
                                cur_frm.reload_doc();
                            }
                        }
                    });
                }
            } else {
                frappe.dom.unfreeze();
            }
        }
    });
}

function transfer_structur_organisation_discounts(frm) {
    if (!frm.doc.__islocal) {
        // Diese Funktion prüft ob zum entsprechenden Dokument bereits ein BG-Job läuft und wenn ja blockiert Sie das Speichern oder weitere BG-Jobs.
        frappe.call({
        'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_any_job_running",
            'args': {
                'doctype': "Quotation",
                'docname': cur_frm.doc.name
            },
            'callback': function(r) {
                var running_job = r.message;
                if (running_job) {
                    frappe.msgprint("Bitte warten Sie bis alle Hintergrundprozesse zu diesem Dokument abgeschlossen sind.");
                } else {
                    // Das ist die eigentliche Funktion
                    frappe.dom.freeze(__("Transferiere Rabatte..."));
                    frappe.call({
                        "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.transfer_structur_organisation_discounts",
                        "args": {
                            "dt": "Quotation",
                            "dn": frm.doc.name
                        },
                        "async": true,
                        "callback": function(response) {
                            var jobname = response.message;
                            if (jobname) {
                                let calc_refresher = setInterval(calc_refresher_handler, 3000, jobname);
                                function calc_refresher_handler(jobname) {
                                    frappe.call({
                                    'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_calc_job_running",
                                        'args': {
                                            'jobname': jobname
                                        },
                                        'callback': function(res) {
                                            if (res.message == 'refresh') {
                                                clearInterval(calc_refresher);
                                                frappe.dom.unfreeze();
                                                calc_structur_organisation_totals(frm);
                                            }
                                        }
                                    });
                                }
                            } else {
                                calc_structur_organisation_totals(frm);
                            }
                        }
                    });
                }
            }
        });
    }
}

function check_hlk_element_allocation(frm) {
    var feedback = '';
    var items = cur_frm.doc.items;
    items.forEach(function(item_entry) {
        if (item_entry.hlk_element.length < 1) {
            feedback = feedback + '<br>#' + String(item_entry.idx);
        }
    });
    return feedback
}

function check_hlk_structur_allocation(frm) {
    var feedback = '';
    var items = cur_frm.doc.hlk_structur_organisation;
    items.forEach(function(item_entry) {
        if (item_entry.parent_element) {
            if (item_entry.parent_element.length < 1) {
                feedback = feedback + '<br>#' + String(item_entry.idx) + ': ' + item_entry.main_element;
            }
        }
    });
    return feedback
}

function calc_valid_to_date(frm) {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.check_calc_valid_to_date",
        "async": false,
        "callback": function(response) {
            if (response.message != 'deactivated') {
                var start = cur_frm.doc.transaction_date;
                var months = parseInt(response.message);
                var new_valid_date = frappe.datetime.add_months(start, months);
                cur_frm.set_value('valid_till', new_valid_date);
            }
        }
    });
}

function change_customer(frm) {
    // Diese Funktion prüft ob zum entsprechenden Dokument bereits ein BG-Job läuft und wenn ja blockiert Sie das Speichern oder weitere BG-Jobs.
    frappe.call({
    'method': "erpnextswiss.erpnextswiss.page.bkp_importer.utils.is_any_job_running",
        'args': {
            'doctype': "Quotation",
            'docname': cur_frm.doc.name
        },
        'callback': function(res) {
            var running_job = res.message;
            if (running_job) {
                frappe.msgprint("Bitte warten Sie bis alle Hintergrundprozesse zu diesem Dokument abgeschlossen sind.");
            } else {
                // Das ist die eigentliche Funktion
                frappe.prompt([
                    {'fieldname': 'customer', 'fieldtype': 'Link', 'label': __('New Customer'), 'reqd': 1, 'options': 'Customer'},
                    {'fieldname': 'adress', 'fieldtype': 'Link', 'label': __('New Address'), 'reqd': 0, 'options': 'Address'},
                    {'fieldname': 'contact', 'fieldtype': 'Link', 'label': __('New Customer'), 'reqd': 0, 'options': 'Contact'}
                ],
                function(values){
                    var args = {
                        'dt': 'Quotation',
                        'record': cur_frm.doc.name,
                        'customer': values.customer
                    }
                    if (values.address) {
                        args["address"] = values.address
                    }
                    if (values.contact) {
                        args["contact"] = values.contact
                    }
                    frappe.call({
                        "method": "erpnextswiss.scripts.crm_tools.change_customer_without_impact_on_price",
                        "args": args,
                        "async": false,
                        "callback": function(response) {
                            cur_frm.reload_doc();
                        }
                    });
                },
                __("Change Customer w/o impact on price"),
                __('Change')
                )
            }
        }
    });
}
