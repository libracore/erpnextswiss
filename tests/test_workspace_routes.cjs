const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "../erpnextswiss/public/js/desk_workspace_routes.js"), "utf8");

function register(names, existing = {}) {
    const frappe = { boot: { workspaces: { pages: names.map(name => ({ name })) } }, re_route: { ...existing } };
    const snapshot = JSON.stringify(frappe.boot);
    vm.runInNewContext(source, { frappe });
    assert.equal(JSON.stringify(frappe.boot), snapshot);
    return frappe;
}

test("only authorized noncanonical aliases are registered", () => {
    const frappe = register(["Schweizer Buchhaltung", "QR-Rechnung & E-Rechnung", "Zahlungsverkehr"]);
    assert.deepEqual(frappe.re_route, {
        erpnextswiss: "Workspaces/Schweizer%20Buchhaltung",
        "qr-rechnung-e-rechnung": "Workspaces/QR-Rechnung%20%26%20E-Rechnung"
    });
    vm.runInNewContext(source, { frappe });
    assert.equal(Object.keys(frappe.re_route).length, 2);
});

test("no workspace permission is invented for an unauthorized user", () => {
    assert.deepEqual(register(["Home"]).re_route, {});
    assert.deepEqual(register([]).re_route, {});
});

test("existing route extensions remain untouched", () => {
    const existing = { erpnextswiss: "custom-start", another: "other-route" };
    assert.deepEqual(register(["Schweizer Buchhaltung"], existing).re_route, existing);
});
