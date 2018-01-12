frappe.pages['match_payments'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Match payments'),
		single_column: true
	});

	frappe.match_payments.make(page);
	frappe.match_payments.run();
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

	},
	run: function() {
		// read open sales invoices
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.match_payments.match_payments.get_open_sales_invoices',
			args: { },
			callback: function(r) {
				if (r.message) {
					var parent = page.main.find(".sales-invoice-table").empty();
                    if (r.message.unpaid_sales_invoices.length > 0) {
                        $(frappe.render_template('sales_invoices_table', r.message)).appendTo(parent);
                    } else {
                        $('<h3>No payment entries to be paid found with status draft</h3>').appendTo(parent);
                    }
				} 
			}
		});
	}
}
