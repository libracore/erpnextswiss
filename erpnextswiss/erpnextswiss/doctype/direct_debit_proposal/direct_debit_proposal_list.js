frappe.listview_settings['Direct Debit Proposal'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Direct Debit Proposal"), function() {
            create_direct_debit_proposal();
        });
    }
}

function create_direct_debit_proposal() {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.doctype.direct_debit_proposal.direct_debit_proposal.create_direct_debit_proposal",
        "callback": function(response) {
            if (response.message) {
                // redirect to the new record
                window.location.href = response.message;
            } else {
                // no records found
                frappe.show_alert( __("No available sales invoices found.") );
            }
        }
    });
}
