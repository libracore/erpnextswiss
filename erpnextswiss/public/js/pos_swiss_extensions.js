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
    var action_bar = document.getElementsByClassName('page-actions');
    var newButton = document.createElement("div");
    if (action_bar.length > 0) {
        // action_bar[0].addChild(newButton); // throws an error
        action_bar[0].innerHTML += "<button class=\"btn btn-primary\"><span class=\"hidden-xs\">ERPNextSwiss</span></button>"; // this will override all buttons
        console.log("button added");
    }
}
