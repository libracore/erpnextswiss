frappe.ui.form.on('Purchase Invoice', {
  validate: function(frm) {
    if (frm.doc.payment_type == "ESR") {
      frappe.provide("erpnextswiss.swiss_common");
      if (!erpnextswiss.swiss_common.check_esr(frm.doc.esr_reference_number)) {
        frappe.msgprint( __("ESR code not valid") ); 
        frappe.validated=false;
      } 
    }

    if ((frm.doc.supplier) && (frm.doc.bill_no)) {
      frappe.call({
        method:"frappe.client.get_list",
        args:{
          doctype: "Purchase Invoice",		
          filters: {
            'supplier': frm.doc.supplier,
            'bill_no': frm.doc.bill_no
          },		
          fields: ['name'],
          async: false
        },
        callback: function(r) {
          r.message.forEach(function(pinv) { 
            if (pinv.name != frm.doc.name) {
              frappe.msgprint(  __("This invoice is already recorded in ") + pinv.name );
              frappe.validated=false;
            }
          });
        }
      });     
    }
  }
});