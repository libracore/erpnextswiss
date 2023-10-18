frappe.listview_settings['Payment Reminder'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Payment Reminders"), function() {
            frappe.prompt(
                [
                    {'fieldname': 'company', 'fieldtype': 'Link', 'options': 'Company', 'label': __('Company'), 'reqd': 1, 'default': frappe.defaults.get_user_default('company')}
                ],
                function(values){
                    create_payment_reminders(values);
                },
                __("Create Payment Reminders"),
                __("Create")
            );
        });  
    }
}

function create_payment_reminders(values) {
    frappe.call({
        'method': "erpnextswiss.erpnextswiss.doctype.payment_reminder.payment_reminder.enqueue_create_payment_reminders",
        'args': {
            'company': values.company
        },
        'callback': function(response) {
            frappe.show_alert( __("Payment Reminders created") );
        }
    });
}
