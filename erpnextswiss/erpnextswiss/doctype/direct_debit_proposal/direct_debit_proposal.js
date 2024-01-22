// Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Direct Debit Proposal', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            // add download pain.008 button on submitted record
            frm.add_custom_button(__("Download bank file"), function() {
                generate_bank_file(frm);
            });
        }
        // filter for bank account
        cur_frm.fields_dict['receive_to_account'].get_query = function(doc) {
            return {
                filters: {
                    "account_type": "Bank"
                }
            }
        }
    },
    validate: function(frm) {
        if (!frm.doc.receive_to_account) {
            frappe.msgprint( __("Please select an account to receive to.") );
            frappe.validated = false;
        }
    },
    on_submit: function(frm) {
        if (!frm.doc.receive_to_account) {
            frappe.msgprint( __("Please select an account to receive to.") );
            frappe.validated = false;
        }
    }
});

function generate_bank_file(frm) {
     console.log("creating file...");
     frappe.call({
        'method': 'create_bank_file',
        'doc': frm.doc,
        'callback': function(r) {
            if (r.message) {
                // prepare the xml file for download
                download("lsv.xml", r.message.content);
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
