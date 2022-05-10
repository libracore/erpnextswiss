frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        if (frm.doc.__islocal||cur_frm.doc.docstatus == '0') {
            frm.add_custom_button(__("Scan Invoice"), function() {
                check_defaults(frm);
            });
        }
        if ((frm.doc.docstatus === 1) && (frm.doc.is_proposed === 1)) {
            cur_frm.dashboard.add_comment(__('This document has been transmitted to the bank for payment'), 'blue', true);
        }
    },
    validate: function(frm) {
        if (frm.doc.payment_type == "ESR") {
            if (frm.doc.esr_reference_number) {
                if (!check_esr(frm.doc.esr_reference_number)) {
                    frappe.msgprint( __("ESR code not valid") ); 
                    frappe.validated=false;
                } 
            } else {
                frappe.msgprint( __("ESR code missing") ); 
                frappe.validated=false;
            }
        }

        if ((frm.doc.supplier) && (frm.doc.bill_no)) {
            frappe.call({
                'method': "frappe.client.get_list",
                'args': {
                    'doctype': "Purchase Invoice",
                    'filters': [
                        ['supplier', '=', frm.doc.supplier],
                        ['bill_no', '=', frm.doc.bill_no],
                        ['docstatus', '<', 2]
                    ],
                    'fields': ['name'],
                    'async': false
                },
                'callback': function(r) {
                    r.message.forEach(function(pinv) { 
                        if (pinv.name != frm.doc.name) {
                            frappe.msgprint(  __("This invoice is already recorded in") + " " + pinv.name );
                            frappe.validated=false;
                        }
                    });
                }
            });     
        }
    },
    supplier: function(frm) {
        if (frm.doc.supplier) {
            frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "Supplier",
                    "name": frm.doc.supplier
                },
                "callback": function(response) {
                    var supplier = response.message;
                    cur_frm.set_value("payment_type", supplier.default_payment_method);
                }
            });
        }
    }
});

function check_defaults(frm) {
    frappe.call({
        'method': "erpnextswiss.scripts.esr_qr_tools.check_defaults",
        'callback': function(response) {
            if (response.message.error) {
                frappe.msgprint(response.message.error);
            } else {
                var default_settings = response.message;
                scan_invoice_code(frm, default_settings);
            }
        }
    });
}

function scan_invoice_code(frm, default_settings) {
    var scan_invoice_txt = __("Scan Invoice");
    frappe.prompt([
        {'fieldname': 'code_scan', 'fieldtype': 'Small Text', 'label': __('Code'), 'reqd': 1}  
    ],
    function(values){
        check_scan_input(frm, default_settings, values.code_scan);
    },
    scan_invoice_txt,
    __('OK')
    )
}

function check_scan_input(frm, default_settings, code_scan) {
    // ESR section
    var regex_9_27 = /[0-9]{13}[>][0-9]{27}[+][ ][0-9]{9}[>]/g; // 0100003949753>120000000000234478943216899+ 010001628>
    var regex_9_27p = /[0-9]{3}[>][0-9]{27}[+][ ][0-9]{9}[>]/g; // 042>120000000000234478943216899+ 010001628>
    var regex_9_16 = /[0-9]{13}[>][0-9]{16}[+][ ][0-9]{9}[>]/g; // 0100003949753>3804137405061016+ 010001628>
    var regex_9_16p = /[0-9]{3}[>][0-9]{16}[+][ ][0-9]{9}[>]/g; // 042>3804137405061016+ 010001628>
    var regex_5_15 = /[<][0-9]{15}[>][0-9]{15}[+][ ][0-9]{5}[>]/g; // <010001000017720>000013230243627+ 73723>
    var regex_5_15p = /[0-9]{15}[+][ ][0-9]{5}[>]/g; // 000013230243627+ 73723>
    if (regex_9_27.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount_int = parseInt(code_scan.split(">")[0].substring(2,10));
        var amount_dec = parseInt(code_scan.split(">")[0].substring(10,12));
        var amount = String(amount_int) + "." + String(amount_dec).padStart(2,'0'); // Betrag in CHF; z.B. 3949.75
        var reference = code_scan.split(">")[1].substring(0,27); // ESR-Referenznummer; z.B. 120000000000234478943216899
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_9_27p.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount = "0.0";
        var reference = code_scan.split(">")[1].substring(0,27); // ESR-Referenznummer; z.B. 120000000000234478943216899
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_9_16.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount_int = parseInt(code_scan.split(">")[0].substring(2,10));
        var amount_dec = parseInt(code_scan.split(">")[0].substring(10,12));
        var amount = String(amount_int) + "." + String(amount_dec).padStart(2,'0'); // Betrag in CHF; z.B. 3949.75
        var reference = code_scan.split(">")[1].substring(0,16); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_9_16p.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount = "0.0";
        var reference = code_scan.split(">")[1].substring(0,16); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_5_15.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(1,3); // Belegart; z.B. 01
        var amount_int = parseInt(code_scan.split(">")[0].substring(7,13));
        var amount_dec = parseInt(code_scan.split(">")[0].substring(14,16));
        var amount = String(amount_int) + "." + String(amount_dec).padStart(2,'0'); // Betrag in CHF; z.B. 3949.75
        var reference = code_scan.split(">")[1].substring(0,15); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,5); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_5_15p.test(code_scan) === true){
        var occupancy = "00";
        var amount = "0.0";
        var reference = code_scan.split(">")[0].substring(0,15); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,5); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else {
        // QR Section 
        var lines = code_scan.split("\n");      // separate lines
        if (lines.length < 28) {
            var invalid_esr_code_line = __("Invalid ESR Code Line or QR-Code");
            frappe.msgprint(invalid_esr_code_line);
        } else {
            var amount = parseFloat(lines[18]);
            var reference = lines[28].replace("\r","").replace("\n","");
            var participant = lines[3].replace("\r","").replace("\n","");
            get_data_based_on_esr(frm, participant, reference, amount, default_settings);
        }
    }
}

function get_data_based_on_esr(frm, participant, reference, amount, default_settings) {
    frappe.call({
        "method": "erpnextswiss.scripts.esr_qr_tools.get_supplier_based_on_esr",
        "args": {
            "participant": participant
        },
        "callback": function(response) {
            var error = response.message.error;
            if (!error) {
                var more_than_one_supplier = response.message.more_than_one_supplier;
                if (!more_than_one_supplier) {
                    // exatly one supplier
                    var supplier = response.message.supplier;
                    show_esr_detail_dialog(frm, participant, reference, amount, default_settings, supplier, []);
                } else {
                    // more than one supplier
                    var _suppliers = response.message.supplier;
                    var suppliers = [];
                    for (var i = 0; i < _suppliers.length; i++) {
                        suppliers.push(_suppliers[i]["supplier_name"] + " // (" + _suppliers[i]["name"] + ")");
                    }
                    suppliers = suppliers.join('\n');
                    show_esr_detail_dialog(frm, participant, reference, amount, default_settings, false, suppliers);
                }
            } else {
                show_esr_detail_dialog(frm, participant, reference, amount, default_settings, false, []);
            }
        }
    });
}

function show_esr_detail_dialog(frm, participant, reference, amount, default_settings, supplier, supplier_list) {
    var field_list = [];
    if (supplier) {
        if (!cur_frm.doc.supplier||cur_frm.doc.supplier == supplier) {
            var supplier_matched_txt = "<p style='color: green;'>" + __("Supplier matched") + "</p>";
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __('Supplier'), 'reqd': 1, 'options': 'Supplier', 'default': supplier, 'description': supplier_matched_txt});
        } else {
            var supplier_missmatch_txt = "<p style='color: orange;'>" + __("Supplier found, but does not match with Invoice Supplier!") + "</p>";
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __('Supplier'), 'reqd': 1, 'options': 'Supplier', 'default': supplier, 'description': supplier_missmatch_txt});
        }
    } else {
        if (supplier_list.length < 1) {
            var supplier_not_found_txt = "<p style='color: red;'>" + __("No Supplier found! Fetched default Supplier.") + "</p>";
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __('Supplier'), 'reqd': 1, 'options': 'Supplier', 'default': default_settings.supplier, 'description': supplier_not_found_txt});
        } else {
            var multiple_supplier_txt = "<p style='color: orange;'>" + __("Multiple Supplier found, please choose one!") + "</p>";
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Select', 'label': __('Supplier'), 'reqd': 1, 'options': supplier_list, 'description': multiple_supplier_txt});
        }
    }
    
    if (cur_frm.doc.grand_total > 0) {
        if (cur_frm.doc.grand_total != parseFloat(amount)) {
            var deviation = parseFloat(amount) - cur_frm.doc.grand_total;
            field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('ESR Amount'), 'read_only': 1, 'default': parseFloat(amount)});
            field_list.push({'fieldname': 'deviation', 'fieldtype': 'Currency', 'label': __('Amount Deviation'), 'read_only': 1, 'default': parseFloat(deviation)});
            if (deviation < 0) {
                field_list.push({'fieldname': 'negative_deviation', 'fieldtype': 'Check', 'label': __('Add negative deviation as discount'), 'default': default_settings.negative_deviation});
            } else {
                field_list.push({'fieldname': 'positive_deviation', 'fieldtype': 'Check', 'label': __('Add positive deviation as additional item'), 'default': default_settings.positive_deviation});
                field_list.push({'fieldname': 'positive_deviation_item', 'fieldtype': 'Link', 'options': 'Item', 'label': __('Positive Deviation Item'), 'default': default_settings.positive_deviation_item});
            }
        } else {
            var esr_amount_matched_txt = "<p style='color: green;'>" + __("ESR / Invoice amount matched") + "</p>";
            field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('ESR Amount'), 'read_only': 1, 'default': parseFloat(amount), 'description': esr_amount_matched_txt});
        }
    } else {
        field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('ESR Amount'), 'read_only': 1, 'default': parseFloat(amount)});
        field_list.push({'fieldname': 'default_item', 'fieldtype': 'Link', 'options': 'Item', 'label': __('Default Item'), 'default': default_settings.default_item});
    }
    
    field_list.push({'fieldname': 'tax_rate', 'fieldtype': 'Float', 'label': __('Tax Rate in %'), 'default': default_settings.default_tax_rate});
    field_list.push({'fieldname': 'reference', 'fieldtype': 'Data', 'label': __('ESR Reference'), 'read_only': 1, 'default': reference});
    field_list.push({'fieldname': 'participant', 'fieldtype': 'Data', 'label': __('ESR Participant'), 'read_only': 1, 'default': participant});
    
    frappe.prompt(field_list,
    function(values){
        if (supplier_list.length > 0) {
            values.supplier = values.supplier.split(" // (")[1].replace(")", "");
        }
        if (frm.doc.__islocal) {
            if ((cur_frm.doc.items.length === 0) || (!cur_frm.doc.items[0].item_code)) {
                fetch_esr_details_to_new_sinv(frm, values);
            } else {
                fetch_esr_details_to_existing_sinv(frm, values);
            }
        } else {
            fetch_esr_details_to_existing_sinv(frm, values);
        }
    },
    __('ESR Details'),
    __('Process')
    )
}

function fetch_esr_details_to_new_sinv(frm, values) {
    // remove all rows
    var tbl = cur_frm.doc.items || [];
    var i = tbl.length;
    while (i--)
    {
        if (!cur_frm.get_field("items").grid.grid_rows[i].doc.item_code) {
            cur_frm.get_field("items").grid.grid_rows[i].remove();
        }
    }
    cur_frm.refresh_field('items');
    
    cur_frm.set_value("supplier", values.supplier);
    cur_frm.set_value("payment_type", 'ESR');
    cur_frm.set_value("esr_reference_number", values.reference);
    
    var rate = (values.amount / (100 + values.tax_rate)) * 100;
    
    var child = cur_frm.add_child('items');
    frappe.model.set_value(child.doctype, child.name, 'item_code', values.default_item);
    frappe.model.set_value(child.doctype, child.name, 'qty', 1.000);
    frappe.model.set_value(child.doctype, child.name, 'rate', rate);
    cur_frm.refresh_field('items');
    setTimeout(function(){
        frappe.model.set_value(child.doctype, child.name, 'rate', rate);
        cur_frm.refresh_field('items');
    }, 1000);
}

function fetch_esr_details_to_existing_sinv(frm, values) {
    cur_frm.set_value("supplier", values.supplier);
    cur_frm.set_value("payment_type", 'ESR');
    cur_frm.set_value("esr_reference_number", values.reference);
    
    if (values.negative_deviation) {
        cur_frm.set_value("apply_discount_on", 'Grand Total');
        var discount_amount = values.deviation * -1;
        cur_frm.set_value("discount_amount", discount_amount);
    }
    
    if (values.positive_deviation) {
        var rate = (values.deviation / (100 + values.tax_rate)) * 100;
        var child = cur_frm.add_child('items');
        frappe.model.set_value(child.doctype, child.name, 'item_code', values.positive_deviation_item);
        frappe.model.set_value(child.doctype, child.name, 'qty', 1.000);
        frappe.model.set_value(child.doctype, child.name, 'rate', rate);
        cur_frm.refresh_field('items');
        setTimeout(function(){
            frappe.model.set_value(child.doctype, child.name, 'rate', rate);
            cur_frm.refresh_field('items');
        }, 1000);
    }
}
