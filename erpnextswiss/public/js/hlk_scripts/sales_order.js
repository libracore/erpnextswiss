frappe.ui.form.on('Sales Order', {
    validate(frm) {
        validate_hlk_element_allocation(frm);
    },
    refresh(frm) {
        // remove update items button
        $('[data-label="Update%20Items"]').remove();
        $('[data-label="Artikel%20aktualisieren"]').remove();
        
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
                     "sales_order": 1,
                     "introduction": 1
                 }
             }
        };
        
        cur_frm.fields_dict['closing_text_template'].get_query = function(doc) {
             return {
                 filters: {
                     "sales_order": 1,
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
        
        if (!frm.doc.__islocal && cur_frm.doc.docstatus == '1') {
            frm.add_custom_button(__("Teilrechnung"), function() {
                if (cur_frm.is_dirty()) {
                    frappe.msgprint(__("Please save Document first."));
                } else {
                    erstelle_teilrechnung_pop_up(frm);
                }
            }, __("Create"));
        }
        
        frappe.call({
            "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.check_for_changed_line_items",
            "args": {
                "record": frm.doc.name
            },
            "async": false,
            "callback": function(response) {
                if (response.message == 'changed') {
                    cur_frm.reload_doc();
                }
            }
        });
    }
})

function transfer_special_discounts(frm) {
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

function erstelle_teilrechnung_pop_up(frm) {
    var struktur_elemente = get_all_strukturelemente(frm);
    var fields = [];
    struktur_elemente.forEach(function(entry) {
        var charged = 100;
        var hlk_structur_organisation = cur_frm.doc.hlk_structur_organisation;
        hlk_structur_organisation.forEach(function(y) {
            if (y.main_element == entry) {
                charged = y.charged;
            }
        });
        if (charged < 100) {
            fields.push({
                'fieldname': entry,
                'fieldtype': 'Percent',
                'label': 'Arbeitsfortschritt in % von ' + entry,
                'default': charged,
                'reqd': 1,
                'description': 'Bereits verrechneter Arbeitsfortschritt: ' + String(charged) + '%'
            });
        }
    });
    if (!fields.length > 0) {
        frappe.msgprint("Es wurden alle Positionen zu 100% verrechnet");
        
    } else {
        frappe.prompt(
        fields,
        function(values){
            frappe.msgprint("Die Teilrechnung wird erstellt, bitte haben Sie einwenig Gedult.", "Bitte warten");
            setTimeout(function(){ 
                for (const [key, value] of Object.entries(values)) {
                    frappe.call({
                        "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.set_amount_to_bill",
                        "args": {
                            "record": frm.doc.name,
                            'element': key,
                            'value': value
                        },
                        "async": false
                    });
                }
                erstelle_teilrechnung(frm);
            }, 1000);
        },
        'Erstellung Teilrechnung',
        'Erstellen'
        )
    }
}

function get_all_strukturelemente(frm) {
    var struktur_elemente = [];
    var items = cur_frm.doc.items;
    items.forEach(function(entry) {
        if ((entry.qty > 0)&&(entry.hlk_element)) {
            if(struktur_elemente.indexOf(entry.hlk_element) === -1) {
                struktur_elemente.push(entry.hlk_element);
            }
        }
    });
    return struktur_elemente;
}

function erstelle_teilrechnung(frm) {
    frappe.model.open_mapped_doc({
        "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.make_sales_invoice",
        "frm": cur_frm
    })
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
    if (!frm.doc.__islocal) {
        frappe.dom.freeze(__("Calc HLK Totals..."));
        frappe.call({
            "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.calc_structur_organisation_totals",
            "args": {
                "dt": "Sales Order",
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
}

function transfer_structur_organisation_discounts(frm) {
    if (!frm.doc.__islocal) {
        frappe.call({
            "method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.transfer_structur_organisation_discounts",
            "args": {
                "dt": "Sales Order",
                "dn": frm.doc.name
            },
            "async": false,
            "callback": function(response) {
                calc_structur_organisation_totals(frm);
            }
        });
    }
}

function check_hlk_element_allocation(frm) {
    var feedback = '';
    var items = cur_frm.doc.items;
    items.forEach(function(item_entry) {
        if (item_entry.hlk_element == null) {
            feedback = feedback + '<br>#' + String(item_entry.idx);
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
    frappe.prompt([
        {'fieldname': 'customer', 'fieldtype': 'Link', 'label': __('New Customer'), 'reqd': 1, 'options': 'Customer'},
        {'fieldname': 'adress', 'fieldtype': 'Link', 'label': __('New Address'), 'reqd': 0, 'options': 'Address'},
        {'fieldname': 'contact', 'fieldtype': 'Link', 'label': __('New Customer'), 'reqd': 0, 'options': 'Contact'}
    ],
    function(values){
        var args = {
            'dt': 'Sales Order',
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
