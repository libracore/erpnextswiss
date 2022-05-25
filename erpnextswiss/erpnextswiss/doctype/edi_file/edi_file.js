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
                    frappe.model.set_value(child.doctype, child.name, 'rate', details.rate);
                    frappe.model.set_value(child.doctype, child.name, 'gtin', details.gtin);
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
