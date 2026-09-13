// Frappe's EditorJS readiness does not await ShortcutWidget.set_actions() counts.
// This runs in the browser against the native workspace data and rendered blocks.
function workspaceShortcutsReady(target) {
    const workspace = window.frappe?.workspace;
    const panel = document.querySelector("#page-Workspaces .layout-main-section");
    const shortcuts = workspace?.page_data?.shortcuts?.items;
    const singleTypes = window.frappe?.boot?.single_types;
    if (workspace?._page?.name !== target || !panel || !Array.isArray(shortcuts)
        || !Array.isArray(workspace.content) || !Array.isArray(singleTypes)) return false;

    const unescape = value => frappe.utils.unescape_html(value);
    const expected = workspace.content.filter(block => block.type === "shortcut")
        .map(block => ({ name: block.data.shortcut_name,
            data: shortcuts.find(item => unescape(item.label) === unescape(__(block.data.shortcut_name))) }))
        .filter(item => item.data);
    const rendered = Array.from(panel.querySelectorAll(".ce-block [shortcut_name]"));
    if (rendered.length !== expected.length) return false;

    return expected.every(({ name, data }) => {
        const matches = rendered.filter(block => block.getAttribute("shortcut_name") === name);
        if (matches.length !== 1) return false;
        const widget = matches[0].querySelector(".shortcut-widget-box");
        if (!widget) return false;
        const needsCount = data.type === "DocType" && data.doc_view !== "New"
            && !singleTypes.includes(data.link_to);
        if (!needsCount) return true;
        const count = widget.querySelector(".indicator-pill");
        return Boolean(count && count.textContent.trim() !== "");
    });
}

module.exports = { workspaceShortcutsReady };
