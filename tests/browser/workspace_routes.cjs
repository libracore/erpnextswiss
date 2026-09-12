const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

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

async function inspect(page, route, workspace, name) {
    await page.goto(base + "/desk/" + route, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(target => window.frappe?.workspace?._page?.name === target
        && frappe.workspace.editor, workspace, { timeout: 45000 });
    await page.evaluate(async () => {
        await frappe.workspace.editor.isReady;
        await document.fonts.ready;
    });
    const panel = page.locator("#page-Workspaces .layout-main-section");
    await panel.locator(".ce-block").first().waitFor();
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
    await page.screenshot({ path: path.join(output, name + ".png"), fullPage: true,
        animations: "disabled", caret: "hide" });
    return snapshot;
}

async function main() {
    fs.mkdirSync(output, { recursive: true });
    const browser = await chromium.launch({ headless: true });
    const results = [];
    try {
        for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
            const context = await browser.newContext({ viewport, reducedMotion: "reduce" });
            try {
                const response = await context.request.post(base + "/api/method/login", {
                    form: { usr: "Administrator", pwd: "admin" }
                });
                assert.ok(response.ok(), "Synthetic CI site login must succeed");
                const page = await context.newPage();
                const errors = [];
                page.on("pageerror", error => errors.push(error.message));
                for (const [alias, workspace] of Object.entries(routes)) {
                    const label = viewport.width + "-" + alias;
                    const canonical = await inspect(page, "Workspaces/" + encodeURIComponent(workspace), workspace, label + "-direct");
                    const legacy = await inspect(page, alias, workspace, label + "-legacy");
                    assert.deepEqual(legacy, canonical, "Old URL must preserve Workspace text and block geometry: " + label);
                    const linked = await inspect(page, "kt-swiss-route-" + alias, workspace, label + "-linked-page");
                    assert.deepEqual(linked, canonical, "Renamed Page references must preserve Workspace rendering: " + label);
                    results.push({ viewport, alias, workspace, blocks: canonical.blocks.length, result: "pass" });
                }
                assert.deepEqual(errors, [], "Navigation must not cause uncaught JavaScript errors");
            } finally {
                await context.close();
            }
        }
    } finally {
        await browser.close();
        fs.writeFileSync(path.join(output, "results.json"), JSON.stringify(results, null, 2));
    }
    console.log("PASS " + results.length + " workspace route comparisons (direct, legacy and retained Page; desktop/mobile)");
}

main().catch(error => { console.error(error); process.exitCode = 1; });
