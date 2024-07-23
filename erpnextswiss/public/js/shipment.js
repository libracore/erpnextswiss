frappe.ui.form.on('Shipment', {
    refresh(frm) {
        if (frm.doc.__islocal) {
            // set default pick times
            cur_frm.set_value("pickup_from", "16:00:00");
            cur_frm.set_value("pickup_to", "19:00:00");
            cur_frm.set_value("pickup_date", frappe.datetime.get_today()); // frappe.datetime.add_days( frappe.datetime.get_today(), 1)
        }
    },
    on_submit(frm) {
        frappe.call({
            'method': 'erpnextswiss.erpnextswiss.planzer.create_shipment',
            'args': {
                'shipment_name': frm.doc.name
            },
            'callback': function(response) {
                if (response.message) {
                    show_alert( response.message );
                }
            }
        });
    }
});
