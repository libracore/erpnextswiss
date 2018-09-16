console.log("Loading POS extensions...");

frappe.pages['pos'].refresh = function (wrapper) {
    // add entries to action menu
    cur_page.page.page.add_action_item("ERPNextSwiss", function() {
        frappe.msgprint("ERPNextSwiss!");
    });    
}
