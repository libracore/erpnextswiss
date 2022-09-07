// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.listview_settings['Municipality'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Import Municipality"), function() {
            // clean file browser cache
            if (document.getElementById("input_file")) {
                document.getElementById("input_file").outerHTML = "";
            }
            var dlg = new frappe.ui.Dialog({
                'title': __("Import Municipality"),
                'fields': [
                    {'fieldname': 'ht', 'fieldtype': 'HTML'}
                ],
                primary_action: function() {
                    dlg.hide();
                    var file = document.getElementById("input_file").files[0];
                    import_municipality(file);
                },
                primary_action_label: __("Import")
            });
            dlg.fields_dict.ht.$wrapper.html('<input type="file" id="input_file" />');
            dlg.show();
        });
    }
}

function import_municipality(file, meeting) {    
    // read the file
    if (file) {
        // create new reader instance 
        var reader = new FileReader();
        reader.onload = function(e) {
            // read the file 
            var data = e.target.result;
            // process file
            frappe.call({
                "method": "erpnextswiss.erpnextswiss.doctype.municipality.municipality.enqueue_import_municipality",
                "args": {
                    "content": data
                },
                "callback": function(response) {
                    if (response.message) {
                        frappe.show_alert(response.message.result);
                    }
                }
            });
        }
        // assign an error handler event
        reader.onerror = function (event) {
            frappe.msgprint(__("Error reading file"), __("Error"));
        }
        reader.readAsText(file, "UTF-8");
    }
    else
    {
        frappe.msgprint(__("Please select a file."), __("Information"));
    }
}
