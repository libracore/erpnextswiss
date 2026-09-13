const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { compareScreenshots } = require("./compare-screenshots.cjs");
const { workspaceShortcutsReady } = require("./workspace-readiness.cjs");

const base = "http://127.0.0.1:8000";
const output = path.join(__dirname, "artifacts");
const routes = {
    erpnextswiss: "Schweizer Buchhaltung",
    "schweizer-buchhaltung": "Schweizer Buchhaltung",
    zahlungsverkehr: "Zahlungsverkehr",
    "qr-rechnung-e-rechnung": "QR-Rechnung & E-Rechnung",
    "schweizer-mwst": "Schweizer MwSt",
    "schweiz-einstellungen": "Schweiz-Einstellungen"
};

async function inspect(page, route, workspace, name, warm = false) {
    if (warm) {
        await page.evaluate(target => frappe.set_route(target), route);
    } else {
        await page.goto(base + "/desk/" + route, { waitUntil: "domcontentloaded" });
    }
    await page.waitForFunction(target => window.frappe?.workspace?._page?.name === target
        && frappe.workspace.editor, workspace, { timeout: 45000 });
    await page.evaluate(async () => {
        await frappe.workspace.editor.isReady;
        await document.fonts.ready;
    });
    const panel = page.locator("#page-Workspaces .layout-main-section");
    await panel.locator(".ce-block").first().waitFor();
    await page.waitForFunction(workspaceShortcutsReady, workspace, { timeout: 45000 });
    await page.mouse.move(0, 0);
    const snapshot = await panel.evaluate(element => ({
        text: element.innerText,
        width: Math.round(element.getBoundingClientRect().width),
        blocks: Array.from(element.querySelectorAll(".ce-block")).map(block => {
            const box = block.getBoundingClientRect();
            return { text: block.innerText, x: Math.round(box.x), y: Math.round(box.y),
                width: Math.round(box.width), height: Math.round(box.height) };
        })
    }));
    assert.ok(snapshot.blocks.length > 0, "Workspace must contain rendered blocks");
    const png = await page.screenshot({ path: path.join(output, name + ".png"), fullPage: true,
        animations: "disabled", caret: "hide" });
    return { snapshot, png };
}

function compare(actual, reference, label, warm = false) {
    assert.deepEqual(actual.snapshot, reference.snapshot, "Workspace text and block geometry: " + label);
    if (warm) return compareScreenshots(actual.png, reference.png, label);
    assert.ok(actual.png.equals(reference.png), "Complete viewport, including navigation, must be identical: " + label);
    return { changedPixels: 0, maxChannelDifference: 0 };
}

async function main() {
    fs.mkdirSync(output, { recursive: true });
    const browser = await chromium.launch({ headless: true });
    const results = [];
    try {
        for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
            const context = await browser.newContext({ viewport, reducedMotion: "reduce" });
            let page;
            try {
                const response = await context.request.post(base + "/api/method/login", {
                    form: { usr: "Administrator", pwd: "admin" }
                });
                assert.ok(response.ok(), "Synthetic CI site login must succeed");
                page = await context.newPage();
                const errors = [];
                page.on("pageerror", error => errors.push(error.message));
                for (const [alias, workspace] of Object.entries(routes)) {
                    const label = viewport.width + "-" + alias;
                    const canonicalRoute = workspace.toLowerCase().replace(/ /g, "-");
                    const canonical = await inspect(page, canonicalRoute, workspace, label + "-direct");
                    const legacy = await inspect(page, alias, workspace, label + "-legacy");
                    compare(legacy, canonical, "Old URL: " + label);
                    const linked = await inspect(page, "kt-swiss-route-" + alias, workspace, label + "-linked-page");
                    compare(linked, canonical, "Renamed Page reference: " + label);
                    const warmComparisons = [];
                    for (let visit = 1; visit <= 2; visit++) {
                        const other = workspace === "Schweiz-Einstellungen" ? "Schweizer Buchhaltung" : "Schweiz-Einstellungen";
                        await page.evaluate(target => frappe.set_route(frappe.router.slug(target)), other);
                        await page.waitForFunction(target => frappe.workspace?._page?.name === target, other);
                        const reopened = await inspect(page, "kt-swiss-route-" + alias, workspace, label + "-reopened-" + visit, true);
                        warmComparisons.push(compare(reopened, canonical, "Repeated in-app Page visit " + visit + ": " + label, true));
                    }
                    results.push({ viewport, alias, workspace, blocks: canonical.snapshot.blocks.length,
                        repeatedVisits: 2, coldViewportIdentical: true, warmComparisons, result: "pass" });
                }
                assert.deepEqual(errors, [], "Navigation must not cause uncaught JavaScript errors");
            } catch (error) {
                if (page && !page.isClosed()) {
                    await page.screenshot({ path: path.join(output, viewport.width + "-failure.png"), fullPage: true });
                    fs.writeFileSync(path.join(output, viewport.width + "-failure.json"), JSON.stringify({
                        url: page.url(), error: String(error),
                        state: await page.evaluate(() => ({ route: frappe.get_route(),
                            workspace: frappe.workspace?._page?.name }))
                    }, null, 2));
                }
                throw error;
            } finally {
                await context.close();
            }
        }
    } finally {
        await browser.close();
        fs.writeFileSync(path.join(output, "results.json"), JSON.stringify(results, null, 2));
    }
    console.log("PASS " + results.length + " full-viewport workspace comparisons (direct, legacy, retained Page and repeated visits; desktop/mobile)");
}

main().catch(error => { console.error(error); process.exitCode = 1; });
