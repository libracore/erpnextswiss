frappe.listview_settings['Payment Proposal'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Payment Proposal"), function() {
            prepare_payment_proposal();
        });
    }
}

function prepare_payment_proposal() {
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
                        {'fieldname': 'date', 'fieldtype': 'Date', 'label': __('Include Payments Until'), 'reqd': 1, 'default': d},
                        {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 
                         'default': frappe.defaults.get_default("Company") }
                    ],
                    function(values){
                        create_payment_proposal(values.date, values.company);
                    },
                    __('Payment Proposal'),
                    __('Create')
                );
            } catch (err) {
                frappe.msgprint("Error: " + err.message);
            }
            
        }
    });
 
}

function create_payment_proposal(date, company) {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.create_payment_proposal",
        "args": { "date": date, "company": company },
        "callback": function(response) {
            if (response.message) {
                // redirect to the new record
                window.location.href = response.message;
            } else {
                // no records found
                frappe.show_alert( __("No suitable invoices found.") );
            }
        }
    });
}
