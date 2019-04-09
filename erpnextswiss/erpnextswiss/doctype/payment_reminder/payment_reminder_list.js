frappe.listview_settings['Payment Reminder'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Payment Reminders"), function() {
            frappe.confirm(
                __("Are you sure you want to create payment reminders?"),
                function(){
                    // on yes
                    create_payment_reminders();
                },
                function(){
                    // on cancel
                }
            );
        });
        listview.page.add_menu_item( __("Submit Selected"), function() {
            var method = "erpnextswiss.erpnextswiss.doctype.payment_reminder.payment_reminder.bulk_submit";
            
            listview.call_for_selected_items(method, {'status': 'Submitted'});
        });  
    }
}

function create_payment_reminders() {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.doctype.payment_reminder.payment_reminder.create_payment_reminders",
        "callback": function(response) {
            frappe.show_alert( __("Payment Reminders created") );
        }
    });
}
