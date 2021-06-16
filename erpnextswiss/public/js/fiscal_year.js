frappe.ui.form.on('Fiscal Year', {
    refresh(frm) {
        frm.add_custom_button(__('Update Print'), function() {
            frappe.call({
                'method': "erpnextswiss.erpnextswiss.finance.enqueue_build_long_fiscal_year_print",
                'args': {
                    'fiscal_year': frm.doc.name,
                },
                'callback': function(response) {
                    frappe.show_alert( __("Done") );
                }
            });
            
            frappe.show_alert( __("Started") );
        });
    }
});
