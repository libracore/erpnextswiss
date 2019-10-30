// Copyright (c) 2017-2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Abacus Export File', {
    refresh: function(frm) {
        // download button for submitted documents
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Download'), function() {
                frappe.call({
                    method:"render_transfer_file",
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.message) {
                            // prepare the xml file for download
                            console.log(r.message.content);
                            download("transfer.xml", r.message.content);
                        } 
                    }
                });
            }).addClass("btn-primary");
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
