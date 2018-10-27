frappe.listview_settings['Payment Proposal'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Payment Proposal"), function() {
            create_payment_proposal();
        });
    }
}

function create_payment_proposal() {
    frappe.call({
        "method": "frappe.client.get",
        "args": {
                "doctype": "ERPNextSwiss Settings",
                "name": "ERPNextSwiss Settings"
        },
        "callback": function(response) {
            try {
                var d = new Date();
                d = new Date(d.setDate(d.getDate() + response.message.planning_days));
                frappe.prompt([
                        {'fieldname': 'date', 'fieldtype': 'Date', 'label': 'Include Payments Until', 'reqd': 1, 'default': d}  
                    ],
                    function(values){
                        create_direct_debit_proposal(values.date);
                    },
                    'Payment Proposal',
                    'Create'
                );
            } catch (err) {
                frappe.msgprint("Error: " + err.message);
            }
            
        }
    });
 
}

function create_direct_debit_proposal(date) {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.create_payment_proposal",
        "args": { "date": date },
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
