frappe.provide("erpnextswiss.workspace_routes");

erpnextswiss.workspace_routes.redirect = function(wrapper, workspace_name) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: workspace_name,
		single_column: true
	});
	$('<div class="text-muted">Arbeitsbereich wird geoeffnet...</div>').appendTo(page.main);
	setTimeout(function() {
		frappe.set_route("Workspaces", workspace_name);
	}, 0);
};

frappe.pages["zahlungsverkehr"].on_page_load = function(wrapper) {
	erpnextswiss.workspace_routes.redirect(wrapper, "Zahlungsverkehr");
};
