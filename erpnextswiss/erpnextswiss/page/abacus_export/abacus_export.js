frappe.pages['abacus_export'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Abacus Export'),
		single_column: true
	});

	frappe.abacus_export.make(page);
	frappe.abacus_export.run();
    
    // add the application reference
    frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.abacus_export = {
	start: 0,
	make: function(page) {
		var me = frappe.abacus_export;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('abacus_export', data)).appendTo(me.body);
        
		// attach button handlers
		this.page.main.find(".btn-create-file").on('click', function() {
			var me = frappe.abacus_export;


		});
	},
	run: function() {

	}
}
