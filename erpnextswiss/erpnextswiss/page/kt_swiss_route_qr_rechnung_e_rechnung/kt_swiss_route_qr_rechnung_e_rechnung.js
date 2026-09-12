frappe.pages["kt-swiss-route-qr-rechnung-e-rechnung"].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: "QR-Rechnung & E-Rechnung", single_column: true });
    $('<div class="text-muted">Arbeitsbereich wird geoeffnet...</div>').appendTo(page.main);
    const allowed = (frappe.boot.workspaces?.pages || []).some(item => item.name === "QR-Rechnung & E-Rechnung");
    if (!allowed) {
        frappe.throw(__("Not permitted"));
        return;
    }
    setTimeout(function() { frappe.set_route("Workspaces", "QR-Rechnung & E-Rechnung"); }, 0);
};
