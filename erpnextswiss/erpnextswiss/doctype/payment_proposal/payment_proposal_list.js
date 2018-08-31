frappe.listview_settings['Payment Proposal'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Payment Proposal"), function() {
            create_direct_debit_proposal();
        });
    }
}

function create_direct_debit_proposal() {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.create_payment_proposal",
        "callback": function(response) {
            if (response.message) {
                // redirect to the new record
                window.location.href = ("/desk#Form/Payment Proposal/" + response.message);
            } else {
                // no records found
                frappe.show_alert( __("No suitable invoices found.") );
            }
        }
    });
}
