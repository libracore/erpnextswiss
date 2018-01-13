frappe.pages['match_payments'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Match payments'),
		single_column: true
	});

	frappe.match_payments.make(page);
	frappe.match_payments.run(page);
}

frappe.match_payments = {
	start: 0,
	make: function(page) {
		var me = frappe.match_payments;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('match_payments', data)).appendTo(me.body);

		// attach button handlers
		this.page.main.find(".btn-match").on('click', function() {
			var me = frappe.bankimport;
                    
			// get sales invoice
            try {
                var sales_invoice = document.querySelector('input[name="invoice"]:checked').value;
                
                try {
                    // get payment entry
                    var payment_entry = document.querySelector('input[name="payment"]:checked').value;

                    //frappe.msgprint("Match " + sales_invoice + " with " + payment_entry);
                			
                    // enable waiting gif
                    page.main.find(".waiting-gif").removeClass("hide");
                    
                    // call match method 
                    frappe.call({
                        method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.match',
                        args: {
                            'sales_invoice': sales_invoice,
                            'payment_entry': payment_entry
                        },
                        callback: function(r) {
                            if (r.message) {
                                //frappe.msgprint("Matched!");
                                
                                submit(r.message.payment_entry, page);
                            } 
                        }
                    }); 
                }
                catch (err) {
                     frappe.msgprint( __("Please select a payment entry.") );
                }
            }
            catch (err) {
                frappe.msgprint( __("Please select a sales invoice.") );
            }

		});

	},
	run: function(page) {
		// read unpaid sales invoices
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.get_open_sales_invoices',
			args: { },
			callback: function(r) {
				if (r.message) {
					var parent = page.main.find(".sales-invoice-table").empty();
                    if (r.message.unpaid_sales_invoices.length > 0) {
                        $(frappe.render_template('sales_invoice_table', r.message)).appendTo(parent);
                    } else {
                        $('<h3>No unpaid sales invoices found.</h3>').appendTo(parent);
                    }
				} 
			}
		});
        // read unallocated payment entries
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.get_unallocated_payment_entries',
			args: { },
			callback: function(r) {
				if (r.message) {
					var parent = page.main.find(".payment-table").empty();
                    if (r.message.unallocated_payment_entries.length > 0) {
                        $(frappe.render_template('payment_entry_table', r.message)).appendTo(parent);
                    } else {
                        $('<h3>No unallocated payment entries found.</h3>').appendTo(parent);
                    }
				} 
			}
		});
	}
}

function submit(payment_entry, page) {
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.submit',
        args: { 
                'payment_entry': payment_entry
            },
        callback: function(r) {
            if (r.message) {
                // disable waiting gif
                page.main.find(".waiting-gif").addClass("hide");
                
                // refresh
                location.reload(); 
            } 
        }
    });
}
