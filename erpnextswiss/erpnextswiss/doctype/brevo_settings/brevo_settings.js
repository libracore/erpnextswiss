// Copyright (c) 2024-2026, libracore AG and contributors
// For license information, please see license.txt

frappe.ui.form.on('Brevo Settings', {
    refresh: function(frm) {
        if (frm.doc.api_key) {
            frm.add_custom_button(__("Fetch contacts"), function() {
                fetch_contacts(frm);
            });
            frm.add_custom_button(__("Fetch lists"), function() {
                fetch_lists(frm);
            });
            frm.add_custom_button(__("Fetch campaigns"), function() {
                fetch_campaigns(frm);
            });
        }
    }
});

function fetch_contacts(frm) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.brevo_settings.brevo_settings.fetch_contacts',
        'freeze': true,
        'freeze_message': __("Retrieving contacts... please stay tuned..."),
        'callback': function(response) {
            frappe.msgprint(response.message);
        }
    });
}

function fetch_lists(frm) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.brevo_settings.brevo_settings.fetch_lists',
        'args': {
            'with_folders': 1
        },
        'freeze': true,
        'freeze_message': __("Retrieving lists... please hang tight..."),
        'callback': function(response) {
            let html = "<table class='table'>";
            html += "<tr><th>ID</th><th>Name</th><th>Folder</th><th>Subscribers</th></tr>";
            let lists = response.message;
            for (let i = 0; i < lists.length; i++) {
                html += "<tr><td>" + lists[i].id 
                     + "</td><td>" + lists[i].name
                     + "</td><td>" + lists[i].folder_name
                     + "</td><td>" + lists[i].uniqueSubscribers + " subscribers</td></tr>";
            }
            html += "</table>";
            frappe.msgprint(html);
        }
    });
}

function fetch_campaigns(frm) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.brevo_settings.brevo_settings.fetch_campaigns',
        'freeze': true,
        'freeze_message': __("Retrieving contacts... please stay tuned..."),
        'callback': function(response) {
            frappe.msgprint(response.message);
        }
    });
}
