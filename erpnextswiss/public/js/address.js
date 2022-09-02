frappe.ui.form.on('Address', {
    refresh(frm) {
        if ((frm.doc.links) && (frm.doc.links.length > 0)) {
            frappe.call({
                'method': 'erpnextswiss.erpnextswiss.zefix.is_zefix_enabled',
                'callback': function(response) {
                    if (response.message === 1) {
                        frm.add_custom_button(__("From Zefix"), function() {
                            frappe.call({
                                'method': 'erpnextswiss.erpnextswiss.zefix.get_address_from_link',
                                'args': {'dt': frm.doc.links[0].link_doctype, 'dn': frm.doc.links[0].link_name},
                                'callback': function(response) {
                                    if (response.message) {
                                        cur_frm.set_value('address_line1', response.message.street);
                                        if (cur_frm.doc.plz) { 
                                            cur_frm.set_value('plz', response.message.pincode);
                                        }
                                        cur_frm.set_value('pincode', response.message.pincode);
                                        cur_frm.set_value('city', response.message.city);
                                        cur_frm.set_value('state', response.message.canton);
                                    } else {
                                        frappe.show_alert( __("Nothing found. Is the tax ID set?") );
                                    }
                                }
                            });
                        });
                    }
                }
            });
        }
    }
});
