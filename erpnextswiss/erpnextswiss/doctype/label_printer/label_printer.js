// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Label Printer', {
	refresh: function(frm) {
		frm.add_custom_button(__("Create Test PDF"), function() {
			create_test_pdf(frm);
		}).addClass("btn-primary");
	}
});

function create_test_pdf(frm) {
    var w = window.open(
	    frappe.urllib.get_full_url("/api/method/erpnextswiss.erpnextswiss.doctype.label_printer.label_printer.download_label"  
			    + "?label_reference=" + encodeURIComponent(frm.doc.name)
			    + "&content=" + encodeURIComponent(frm.doc.test_content))
    );
    if (!w) {
	    frappe.msgprint(__("Please enable pop-ups")); return;
    }
    
}
