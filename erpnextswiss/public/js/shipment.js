frappe.ui.form.on('Shipment', {
    on_submit(frm) {
        frappe.call({
            'method': 'erpnextswiss.erpnextswiss.planzer.create_shipment',
            'args': {
                'shipment_name': frm.doc.name
            },
            'callback': function(response) {
                if (response.message) {
                    frappe.showalert( response.message );
                }
            }
        });
    }
});
