frappe.listview_settings['Payment Reminder'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Payment Reminders"), function() {
            reate_payment_reminders();
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
