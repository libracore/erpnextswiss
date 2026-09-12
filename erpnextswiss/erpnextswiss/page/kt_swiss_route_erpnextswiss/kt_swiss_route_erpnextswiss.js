frappe.pages["kt-swiss-route-erpnextswiss"].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: "Schweizer Buchhaltung", single_column: true });
    $('<div class="text-muted">Arbeitsbereich wird geoeffnet...</div>').appendTo(page.main);
    const allowed = (frappe.boot.workspaces?.pages || []).some(item => item.name === "Schweizer Buchhaltung");
    if (!allowed) {
        frappe.throw(__("Not permitted"));
        return;
    }
    setTimeout(function() { frappe.set_route("Workspaces", "Schweizer Buchhaltung"); }, 0);
};
