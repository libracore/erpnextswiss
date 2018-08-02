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
		// set beginning of the year as start and today as current date
		var today = new Date();
		var dd = today.getDate();
		if (dd < 10) { dd = "0" + dd; }
		var mm = today.getMonth() + 1; 	//January is 0!
		if (mm < 10) { mm = "0" + mm; }
		var yyyy = today.getFullYear();
		var input_start = document.getElementById("start_date");
		input_start.value = yyyy + "-01-01";
		var input_end = document.getElementById("end_date");
		input_end.value = yyyy + "-" + mm + "-" + dd;
		
		// attach change handlers
		input_start.onchange = function() { frappe.abacus_export.update_preview(); };
		input_end.onchange = function() { frappe.abacus_export.update_preview(); };
	},
	update_preview: function() {
		console.log("here...");
		preview_container = document.getElementById("preview");
		preview_container.innerHTML = "";
		preview_container.innerHTML += "Preview!";
	}
}

