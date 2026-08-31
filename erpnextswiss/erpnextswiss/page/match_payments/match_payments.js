frappe.pages['match_payments'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Match payments'),
		single_column: true
	});

	frappe.match_payments.make(page);
	frappe.match_payments.run(page);
    
    // add the application reference
    frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.match_payments = {
	start: 0,
	make: function(page) {
		var me = frappe.match_payments;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('match_payments', data)).appendTo(me.body);

        // add menu button
        this.page.add_menu_item(__("Open bank import"), function() {
            // navigate to bank import tool
            window.location.href="/app/bankimport";
		});
        
		// attach button handlers
		this.page.main.find(".btn-match").on('click', function() {                   
            match(page);
		});
        
        this.page.main.find(".btn-auto-match-id").on('click', function() {                   
            auto_match(page, "docid");
		});

        this.page.main.find(".btn-auto-match-esr").on('click', function() {                   
            auto_match(page, "esr");
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
                        $('<p class="text-muted">' + __("No unpaid sales invoices found.") + '</p>').appendTo(parent);
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
                        $('<p class="text-muted">' + __("No unallocated payment entries found.") + '</p>').appendTo(parent);
                    }
				} 
			}
		});
	},
    start_wait: function() {
        document.getElementById("waitingScreen").style.display = "block";
    },
    end_wait: function() {
        document.getElementById("waitingScreen").style.display = "none";
    }
}

function match(page) {
    // get sales invoice
    try {
        var sales_invoice = document.querySelector('input[name="invoice"]:checked').value;
        
        try {
            // get payment entry
            var payment_entry = document.querySelector('input[name="payment"]:checked').value;

            //frappe.msgprint("Match " + sales_invoice + " with " + payment_entry);
                    
            // enable waiting gif
            frappe.match_payments.start_wait();
            
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
}

function auto_match(page, method="docid") {
    //try {                   
        // enable waiting gif
        frappe.match_payments.start_wait();
        
        // call match method 
        frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.auto_match',
            args: {
                'method': method
            },
            callback: function(r) {
                if (r.message) {   
                    if (r.message.payments.length > 0) {    
                        frappe.show_alert( __("Matched {0} sales invoices.").replace("{0}", String(r.message.payments.length)));      
                        submit_all(r.message.payments, page);
                    } else {
                        completed(page, false);
                        frappe.show_alert( __("No matches found.") );
                    }
                } 
            }
        }); 
    //}
    //catch (err) {
    //     frappe.msgprint( __("Please select a payment entry.") );
    //}
}

function submit(payment_entry, page) {
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.submit',
        args: { 
                'payment_entry': payment_entry
            },
        callback: function(r) {
            if (r.message) {
                completed(page);
            } 
        }
    });
}

function submit_all(payments, page) {
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.submit_all',
        args: { 
                'payment_entries': payments
            },
        callback: function(r) {
            if (r.message) {
                completed(page);
            } 
        }
    });
}

function completed(page, reload=true) {
    // disable waiting gif
    frappe.match_payments.end_wait();
    
    // refresh
    if (reload) {
        location.reload(); 
    }
}
