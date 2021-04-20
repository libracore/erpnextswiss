frappe.pages['worktime-overview'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Worktime Overview',
		single_column: true
	});
}