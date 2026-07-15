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
        // prevent lower case characters in IBANs
        if (frm.doc.iban) {
            cur_frm.set_value("iban", frm.doc.iban.toUpperCase());
        }
        if (frm.doc.esr_participation_number) {
            cur_frm.set_value("esr_participation_number", frm.doc.esr_participation_number.toUpperCase());
        }
        
        // verify IBAN vs. ESR-/QR-IBAN
        if ((frm.doc.iban) 
            && (frm.doc.iban.startsWith("CH"))
            && (frm.doc.iban.replaceAll(" ", "")[4] === "3")) {
                frappe.msgprint( __("The provided IBAN is a QR-IBAN, moving it to QR-IBAN field"), __("Notification") );
                cur_frm.set_value("esr_participation_number", frm.doc.iban);
                cur_frm.set_value("iban", "");
        }
        if ((frm.doc.esr_participation_number) 
            && (frm.doc.esr_participation_number.startsWith("CH")) 
            && (frm.doc.esr_participation_number.replaceAll(" ", "")[4] !== "3")) {
                frappe.msgprint( __("The provided QR-IBAN is an IBAN, moving it to IBAN field"), __("Notification") );
                cur_frm.set_value("iban", frm.doc.esr_participation_number);
                cur_frm.set_value("esr_participation_number", "");
        }
        
        if ((frm.doc.default_payment_method === "IBAN") && (!frm.doc.iban) && (frm.doc.esr_participation_number)) {
            // default to ESR if ESR number is available but IBAN is not
            cur_frm.set_value("default_payment_method", "ESR");
        } else if ((frm.doc.default_payment_method === "ESR") && (!frm.doc.esr_participation_number) && (frm.doc.iban)) {
            // default to ESR if ESR number is available but IBAN is not
            cur_frm.set_value("default_payment_method", "IBAN");
        }
    }
});
