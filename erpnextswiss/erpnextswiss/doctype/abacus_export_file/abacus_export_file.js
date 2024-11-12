// Copyright (c) 2017-2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Abacus Export File', {
    refresh: function(frm) {
        // download button for submitted documents
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Download'), function() {
                var url = "/api/method/erpnextswiss.erpnextswiss.doctype.abacus_export_file.abacus_export_file.download_xml"  
                        + "?docname=" + encodeURIComponent(frm.doc.name);
                var w = window.open(
                     frappe.urllib.get_full_url(url)
                );
                if (!w) {
                    frappe.msgprint(__("Please enable pop-ups")); return;
                }

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
        'freeze': true,
        'freeze_message': __("Evaluating result file... hang tight..."),
        'callback': function(response) {
            var d = new frappe.ui.Dialog({
                'fields': [
                    {
                        'fieldname': 'ht', 
                        'fieldtype': 'HTML'
                    }
                ],
                'primary_action': function(){
                    navigator.clipboard.writeText(response.message).then(function() {
                        frappe.show_alert( __("HTML copied to clipboard") );
                      }, function() {
                         frappe.show_alert( __("Clipboard access failed") );
                    });
                },
                'primary_action_label': __("Copy"),
                'title': __("Comparison")
            });
            d.fields_dict.ht.$wrapper.html(response.message);
            d.show();
            
            // hack: increase dialog width
            setTimeout(function () {
                var modals = document.getElementsByClassName("modal-dialog");
                if (modals.length > 0) {
                    modals[modals.length - 1].style.width = "1000px";
                }
            }, 300);
        }
    });
}
