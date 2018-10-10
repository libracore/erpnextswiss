console.log("Loading POS extensions...");

frappe.pages['pos'].refresh = function (wrapper) {
    // add entries to action menu
    cur_page.page.page.add_action_item("Tagesabschluss erstellen", function() {
        frappe.msgprint("Tagesabschluss erstellt");
    });
    cur_page.page.page.add_action_item("Wochenabschluss erstellen", function() {
        frappe.msgprint("Wochenabschluss erstellt");
    });
    cur_page.page.page.add_action_item("Rücknahme buchen", function() {
        frappe.msgprint("Rückname erstellt");
    });
}
