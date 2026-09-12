frappe.pages["kt-swiss-route-zahlungsverkehr"].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: "Zahlungsverkehr", single_column: true });
    $('<div class="text-muted">Arbeitsbereich wird geoeffnet...</div>').appendTo(page.main);
    const allowed = (frappe.boot.workspaces?.pages || []).some(item => item.name === "Zahlungsverkehr");
    if (!allowed) {
        frappe.throw(__("Not permitted"));
        return;
    }
    setTimeout(function() { frappe.set_route("Workspaces", "Zahlungsverkehr"); }, 0);
};
