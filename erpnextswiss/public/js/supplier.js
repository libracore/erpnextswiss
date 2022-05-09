frappe.ui.form.on('Supplier', {
    supplier_name(frm) {
        if ((frm.doc.supplier_name) && (!frm.doc.tax_id)) {
            frappe.call({
                'method': 'erpnextswiss.erpnextswiss.zefix.get_party_tax_id',
                'args': {'party_name': frm.doc.supplier_name},
                'callback': function(response) {
                    if (response.message) {
                        cur_frm.set_value('tax_id', response.message.uid);
                        cur_frm.set_value('supplier_name', response.message.name);
                    }
                }
            });
        }
    },
    before_save(frm) {
        if ((frm.doc.default_payment_method === "IBAN") && (!frm.doc.iban) && (frm.doc.esr_participation_number)) {
            // default to ESR if ESR number is available but IBAN is not
            cur_frm.set_value("default_payment_method", "ESR");
        }
    }
});
