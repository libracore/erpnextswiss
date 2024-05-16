// Copyright (c) 2017-2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Abacus Export File', {
    refresh: function(frm) {
        // download button for submitted documents
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Download'), function() {
                frappe.call({
                    'method': "render_transfer_file",
                    'doc': frm.doc,
                    'callback': function(r) {
                        if (r.message) {
                            // prepare the xml file for download
                            console.log(r.message.content);
                            download("transfer.xml", r.message.content);
                        } 
                    }
                });
            }).addClass("btn-primary");
            
            frm.add_custom_button(__('Compare Result'), function() {
                compare_result(frm);
            });
        }
        // reset flag function for system managers
        if (frappe.user.has_role("System Manager")) {
            frm.page.add_menu_item(__("Reset export flags"), function() {
                frappe.call({
                    method:"reset_export_flags",
                    doc: frm.doc,
                    callback: function(response) {
                       frappe.show_alert( __("Done!") );
                    }
                });
            });
        }
    }
});

function download(filename, content) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

function compare_result(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'ht', 'fieldtype': 'HTML'}
        ],
        'primary_action': function(){
            // read the file
            var xml_file = document.getElementById("result_xml").files[0];
            if (xml_file.name.toLowerCase().endsWith(".xml")) {
                var xml_content = "";
                
                if (xml_file) {
                
                    var reader = new FileReader();
                    reader.onload = function (event) {
                        xml_content = event.target.result;
                        
                        compare_result_xml(xml_content);
                        
                        // hide dialog
                        d.hide();
                    }
                    reader.onerror = function (event) {
                        frappe.msgprint( __("Error reading file"), __("Error") );
                    }
                    
                    reader.readAsText(xml_file, "ANSI");
                } else {
                    frappe.msgprint( __("Please select a file"), __("Validation"));
                }
            } else {
                frappe.msgprint( __("Please provide an Abacus Result XML file"), __("Validation"));
            }
        },
        'primary_action_label': __('Compare'),
        'title': __("Abacus Result File")
    });
    d.fields_dict.ht.$wrapper.html("<input type='file' id='result_xml' />");
    d.show();
}


function compare_result_xml(xml_content) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.abacus_export_file.abacus_export_file.compare_result_xml',
        'args': {
            'docname': cur_frm.doc.name,
            'xml_content': xml_content
        },
        'callback': function(response) {
            frappe.msgprint(response.message, __("Comparison"));
        }
    });
}
