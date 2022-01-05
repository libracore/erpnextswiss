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
    }
});
