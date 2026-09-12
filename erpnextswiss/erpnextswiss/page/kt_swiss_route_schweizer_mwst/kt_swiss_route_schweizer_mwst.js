frappe.pages["kt-swiss-route-schweizer-mwst"].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: "Schweizer MwSt", single_column: true });
    $('<div class="text-muted">Arbeitsbereich wird geoeffnet...</div>').appendTo(page.main);
    const allowed = (frappe.boot.workspaces?.pages || []).some(item => item.name === "Schweizer MwSt");
    if (!allowed) {
        frappe.throw(__("Not permitted"));
        return;
    }
    setTimeout(function() { frappe.set_route("Workspaces", "Schweizer MwSt"); }, 0);
};
