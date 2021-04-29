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
		var data = {'allowed': 0};
        if (frappe.user.has_role('HR Manager')) {
            data = {'allowed': 1};
        }
		$(frappe.render_template('worktime_overview', data)).appendTo(me.body);

        // attach button handlers
		this.page.main.find("#from").on('change', function() {                   
            frappe.worktime_overview.get_data(page);
		});
        this.page.main.find("#to").on('change', function() {                   
            frappe.worktime_overview.get_data(page);
		});
        this.page.main.find("#view_type").on('change', function() {                   
            frappe.worktime_overview.get_data(page);
		});
	},
	get_data: function(page) {
        var _from_date = $("#from").val();
        var _to_date = $("#to").val();
        var view_type = 'single';
        if ($("#view_type").val() == 'All Employees') {
            view_type = 'all';
        }
        
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
                            'to_date': _to_date,
                            'view_type': view_type
                        },
                    callback: function(r) {
                        if (r.message) {
                            var data = r.message;
                            // create new table
                            $(frappe.render_template('worktime_overview_table', data)).appendTo(me.time_overview);
                            if (view_type == 'single') {
                                var tt = []
                                var at = []
                                tt.push(parseFloat(data.data.target))
                                at.push(parseFloat(data.data.actual))
                                frappe.worktime_overview.make_single_chart(tt, at);
                            } else {
                                var labels = [];
                                var tt = [];
                                var at = [];
                                for (var i = 0; i < data.dataset.length; i++) {
                                    labels.push(data.dataset[i].employee_name);
                                    tt.push(parseFloat(data.dataset[i].target));
                                    at.push(parseFloat(data.dataset[i].actual));
                                }
                                frappe.worktime_overview.make_multi_chart(labels, tt, at);
                            }
                        } 
                    }
                });
                
            }
        } else {
            $("#time_overview_table").remove();
        }
    },
    make_single_chart: function(tt, at) {
        console.log(tt);
        console.log(at);
        const data = {
            labels: ["My Times"
            ],
            datasets: [
                {
                    name: "Target Time", type: "bar",
                    values: tt
                },
                {
                    name: "Actual Time", type: "bar",
                    values: at
                }
            ]
        }

        const chart = new frappe.Chart("#chart", {  // or a DOM element,
                                                    // new Chart() in case of ES6 module with above usage
            title: "",
            data: data,
            type: 'bar', // or 'axis-mixed', 'bar', 'line', 'scatter', 'pie', 'percentage'
            height: 250,
            colors: ['#7cd6fd', '#743ee2']
        })
    },
    make_multi_chart: function(labels, tt, at) {
        const data = {
            labels: labels,
            datasets: [
                {
                    name: "Target Time", type: "bar",
                    values: tt
                },
                {
                    name: "Actual Time", type: "bar",
                    values: at
                }
            ]
        }

        const chart = new frappe.Chart("#chart", {  // or a DOM element,
                                                    // new Chart() in case of ES6 module with above usage
            title: "",
            data: data,
            type: 'bar', // or 'axis-mixed', 'bar', 'line', 'scatter', 'pie', 'percentage'
            height: 250,
            colors: ['#7cd6fd', '#743ee2']
        })
    }
}
