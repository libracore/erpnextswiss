frappe.ui.form.on("Payment Entry", {
  onload: function(frm) {
    try {
      // make sure this entry is a virgin
      if (!frm.doc.name.startsWith("PE-")) { 
	// make sure the parent is a purchase invoice
        var parent = frm.doc.references[0].reference_name;
        if (parent.startsWith("PINV-")) {
          // fetch values from PINV
          load_purchase_invoice_details(frm, parent)

          // load values from supplier
          var supplier_name = frm.doc.party;
          if ((supplier_name != null) && (supplier_name != "")) {
            load_supplier_details(frm, supplier_name);
          }
        }
      }
    }
    catch (err) {
      // frappe.msgprint(err.message);
    }
  }
});

function load_purchase_invoice_details(frm, pinv_name) {
  frappe.call({
    "method": "frappe.client.get",
    "args": {
       "doctype": "Purchase Invoice",
       "name": pinv_name
    },
    "callback": function(response) {
       var pinv = response.message;
       if (pinv) {
          cur_frm.set_value('esr_reference', pinv.esr_reference_number);
          cur_frm.set_value('reference_no', pinv.name);
          cur_frm.set_value('reference_date', pinv.due_date);
          cur_frm.set_value('posting_date', pinv.due_date);
          cur_frm.set_value('transaction_type', pinv.payment_type);
          show_alert(__("Invoice details added"));
       }
    }
  });
}

function load_supplier_details(frm, supplier_name) {
  frappe.call({
    "method": "frappe.client.get",
    "args": {
       "doctype": "Supplier",
       "name": supplier_name
    },
    "callback": function(response) {
       var supplier = response.message;
       if (supplier) {
          cur_frm.set_value('iban', supplier.iban);
          cur_frm.set_value('bic', supplier.bic);
          cur_frm.set_value('esr_participant_number', supplier.esr_participation_number);
          show_alert(__("Supplier data added"));
       }
    }
  });
}
