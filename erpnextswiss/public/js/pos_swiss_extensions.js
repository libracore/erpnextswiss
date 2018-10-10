console.log("Loading POS extensions...");

/* frappe.provide('erpnext.pos');

frappe.pages['pos'].refresh = function (wrapper) {
    console.log(wrapper);
    frappe.msgprint( __("Hello World") ); 
    
    wrapper.pos.frm.page.add_menu_item( __("Greeting"), function() {
       frappe.msgprint( __("Hello World") ); 
    }); 
    console.log(wrapper.pos); // undefined 
    
}

frm.page.add_menu_item( __("Greeting"), function() {
   frappe.msgprint( __("Hello World") ); 
}); */



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
