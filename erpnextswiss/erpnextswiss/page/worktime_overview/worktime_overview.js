frappe.pages['worktime-overview'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Worktime Overview',
		single_column: true
	});
    
    frappe.worktime_overview.make(page);
    
    // add the application reference
    frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.worktime_overview = {
	start: 0,
	make: function(page) {
		var me = frappe.worktime_overview;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('worktime_overview', data)).appendTo(me.body);

        // attach button handlers
		this.page.main.find("#from").on('change', function() {                   
            frappe.worktime_overview.get_data(page);
		});
        this.page.main.find("#to").on('change', function() {                   
            frappe.worktime_overview.get_data(page);
		});
	},
	get_data: function(page) {
        var _from_date = $("#from").val();
        var _to_date = $("#to").val();
        
        if (_from_date && _to_date) {
        
            from_date = new Date($("#from").val());
            to_date = new Date($("#to").val());
            
            if (to_date < from_date) {
                $("#time_overview_table").remove();
                frappe.throw(__("To Date can not be before from date"));
            } else if (to_date.getFullYear() != from_date.getFullYear()) {
                $("#time_overview_table").remove();
                frappe.throw(__("Please choose same year"));
            } else {
                var me = frappe.worktime_overview;
                me.time_overview = $("#time_overview");
                
                // remove old table
                $("#time_overview_table").remove();
                    
                // get data
                frappe.call({
                    method: 'erpnextswiss.erpnextswiss.page.worktime_overview.worktime_overview.get_data',
                    args: {
                            'from_date': _from_date,
                            'to_date': _to_date
                        },
                    callback: function(r) {
                        if (r.message) {
                            var data = r.message;
                            // create new table
                            $(frappe.render_template('worktime_overview_table', data)).appendTo(me.time_overview);
                        } 
                    }
                });
                
            }
        } else {
            $("#time_overview_table").remove();
        }
    }
}
