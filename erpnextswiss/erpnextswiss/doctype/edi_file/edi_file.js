// Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('EDI File', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Download"), function() {
                download_file(frm);
            });
        }
    },
    button_add_item(frm) {
        add_item(frm);
    },
    taxes_template(frm) {
        if (frm.doc.taxes_template) {
            frappe.call({
                'method': 'frappe.client.get',
                'args': {
                    'doctype': "Sales Taxes and Charges Template",
                    'name': frm.doc.taxes_template
                },
                'callback': function(r) {
                    if (r.message) {
                        cur_frm.clear_table("taxes");
                        var taxes_template = r.message;
                        for (var i = 0; i < taxes_template.taxes.length; i++) {
                            // insert item
                            var child = cur_frm.add_child('taxes');
                            frappe.model.set_value(child.doctype, child.name, 'charge_type', taxes_template.taxes[i].charge_type);
                            frappe.model.set_value(child.doctype, child.name, 'row_id', taxes_template.taxes[i].row_id);
                            frappe.model.set_value(child.doctype, child.name, 'account_head', taxes_template.taxes[i].account_head);
                            frappe.model.set_value(child.doctype, child.name, 'description', taxes_template.taxes[i].description);
                            frappe.model.set_value(child.doctype, child.name, 'included_in_print_rate', taxes_template.taxes[i].included_in_print_rate);
                            frappe.model.set_value(child.doctype, child.name, 'accounting_dimensions', taxes_template.taxes[i].accounting_dimensions);
                            frappe.model.set_value(child.doctype, child.name, 'cost_center', taxes_template.taxes[i].cost_center);
                            frappe.model.set_value(child.doctype, child.name, 'rate', taxes_template.taxes[i].rate);
                            frappe.model.set_value(child.doctype, child.name, 'tax_amount', taxes_template.taxes[i].tax_amount);
                            frappe.model.set_value(child.doctype, child.name, 'total', taxes_template.taxes[i].total);
                            frappe.model.set_value(child.doctype, child.name, 'tax_amount_after_discount', taxes_template.taxes[i].tax_amount_after_discount);
                            frappe.model.set_value(child.doctype, child.name, 'base_tax_amount', taxes_template.taxes[i].base_tax_amount);
                            frappe.model.set_value(child.doctype, child.name, 'base_total', taxes_template.taxes[i].base_total);
                            frappe.model.set_value(child.doctype, child.name, 'base_tax_amount_after_discount', taxes_template.taxes[i].base_tax_amount_after_discount);
                            frappe.model.set_value(child.doctype, child.name, 'item_wise_tax_deatil', taxes_template.taxes[i].item_wise_tax_deatil);
                        }
                        cur_frm.refresh_fields("taxes");
                    } 
                }
            });
        }
    }
});

function add_item(frm) {
    frappe.prompt([
        {'fieldname': 'item_code', 'fieldtype': 'Link', 'options': 'Item', 'label': __('Item'), 'reqd': 1}  
    ],
    function(values){
        // get details
        frappe.call({
            'method': 'get_item_details',
            'doc': frm.doc,
            'args': {
                'item_code': values.item_code
            },
            'callback': function(r) {
                if (r.message) {
                    var details = r.message;
                    // insert item
                    var child = cur_frm.add_child('pricat_items');
                    frappe.model.set_value(child.doctype, child.name, 'item_code', details.item_code);
                    frappe.model.set_value(child.doctype, child.name, 'action', details.action);
                    frappe.model.set_value(child.doctype, child.name, 'item_name', details.item_name);
                    frappe.model.set_value(child.doctype, child.name, 'item_group', details.item_group);
                    frappe.model.set_value(child.doctype, child.name, 'rate', details.rate);
                    frappe.model.set_value(child.doctype, child.name, 'retail_rate', details.retail_rate);
                    frappe.model.set_value(child.doctype, child.name, 'gtin', details.gtin);
                    console.log(details);
                    if (details.attributes) {                        
                        for (var a = 0; a < details.attributes.length; a++) {
                            if (details.attributes[a].attribute === "Size") {
                                frappe.model.set_value(child.doctype, child.name, 'size', details.attributes[a].attribute_value);
                            } else if (["Colour", "Color", "Farbe"].includes(details.attributes[a].attribute)) {
                                frappe.model.set_value(child.doctype, child.name, 'colour', details.attributes[a].attribute_value);
                            }
                        }
                    }
                    cur_frm.refresh_fields("pricat_items");
                } 
            }
        });
    },
    __('Add Item'),
    __('Add')
    )
}

function download_file(frm) {
    frappe.call({
        'method': 'download_file',
        'doc': frm.doc,
        'callback': function(r) {
            if (r.message) {
                // prepare the xml file for download
                download("pricat_" + frm.doc.name + ".edi", r.message.content);
            } 
        }
    });
}

function download(filename, content) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}
