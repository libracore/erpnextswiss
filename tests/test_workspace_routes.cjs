const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "../erpnextswiss/public/js/desk_workspace_routes.js"), "utf8");

function register(names, existing = {}) {
    const frappe = { boot: { workspaces: { pages: names.map(name => ({ name })) } }, re_route: { ...existing },
        router: { slug: name => name.toLowerCase().replace(/ /g, "-") } };
    const snapshot = JSON.stringify(frappe.boot);
    vm.runInNewContext(source, { frappe });
    assert.equal(JSON.stringify(frappe.boot), snapshot);
    return frappe;
}

test("only authorized noncanonical aliases are registered", () => {
    const frappe = register(["Schweizer Buchhaltung", "QR-Rechnung & E-Rechnung", "Zahlungsverkehr"]);
    assert.deepEqual(frappe.re_route, {
        erpnextswiss: "schweizer-buchhaltung",
        "qr-rechnung-e-rechnung": "qr-rechnung-&-e-rechnung"
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

const pageDirectory = path.join(__dirname, "../erpnextswiss/erpnextswiss/page");
for (const folder of fs.readdirSync(pageDirectory).filter(name => name.startsWith("kt_swiss_route_"))) {
    test("retained Page redirects on every authorized visit: " + folder, () => {
        const name = folder.replace(/_/g, "-");
        const script = fs.readFileSync(path.join(pageDirectory, folder, folder + ".js"), "utf8");
        const visits = [];
        let title;
        const frappe = { pages: { [name]: {} }, boot: { workspaces: { pages: [] } },
            ui: { make_app_page: options => { title = options.title; return { main: {} }; } },
            router: { slug: name => name.toLowerCase().replace(/ /g, "-") },
            set_route: route => visits.push(route),
            throw: () => { throw new Error("Permission denied"); } };
        vm.runInNewContext(script, { frappe, $: () => ({ appendTo() {} }),
            __: value => value, setTimeout: callback => callback() });
        frappe.pages[name].on_page_load({});
        assert.deepEqual(visits, []);
        frappe.boot.workspaces.pages = [{ name: title }];
        frappe.pages[name].on_page_show();
        frappe.pages[name].on_page_show();
        assert.deepEqual(visits, [frappe.router.slug(title), frappe.router.slug(title)]);
        frappe.boot.workspaces.pages = [];
        assert.throws(() => frappe.pages[name].on_page_show(), /Permission denied/);
        assert.equal(visits.length, 2);
    });
}
