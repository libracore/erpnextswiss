// Native workspace slugs already cover the other four historical URLs.
// Register only the two aliases, and only for workspaces present in this user's boot.
(function () {
    "use strict";
    const aliases = {
        "erpnextswiss": "Schweizer Buchhaltung",
        "qr-rechnung-e-rechnung": "QR-Rechnung & E-Rechnung"
    };
    const allowed = new Set((frappe.boot.workspaces?.pages || []).map(page => page.name));
    for (const [alias, workspace] of Object.entries(aliases)) {
        if (allowed.has(workspace) && !Object.hasOwn(frappe.re_route, alias)) {
            frappe.re_route[alias] = "Workspaces/" + encodeURIComponent(workspace);
        }
    }
})();
