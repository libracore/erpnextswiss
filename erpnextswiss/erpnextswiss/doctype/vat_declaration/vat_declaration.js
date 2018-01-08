// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('VAT Declaration', {
	refresh: function(frm) {

	}
});

frappe.ui.form.on("VAT Declaration", {
  setup: function(frm) {
    // this function is called when a new VAT declaration is created
    // get current month (0..11)
    var d = new Date();
    var n = d.getMonth();
    // define title as Qn YYYY of the last complete quarter
    var title = " / " + d.getFullYear();
    if ((n > (-1)) && (n < 3)) {
        title = "Q04 / " + (d.getFullYear() - 1);
        frm.set_value('start_date', d.getFullYear() + "-10-01");
        frm.set_value('end_date', d.getFullYear() + "-12-31");
    } else if ((n > (2)) && (n < 6)) {
        title = "Q01" + title;
        frm.set_value('start_date', d.getFullYear() + "-01-01");
        frm.set_value('end_date', d.getFullYear() + "-03-31");
    } else if ((n > (5)) && (n < 9)) {
        title = "Q02" + title;
        frm.set_value('start_date', d.getFullYear() + "-04-01");
        frm.set_value('end_date', d.getFullYear() + "-06-30");
    } else {
        title = "Q03" + title;
        frm.set_value('start_date', d.getFullYear() + "-07-01");
        frm.set_value('end_date', d.getFullYear() + "-09-30");
    } 

    frm.set_value('title', title);
  }
});

// get revenues
function get_revenue() {
    // total revenues is the sum of all sales invoices in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_revenue',
        args: { },
        callback: function(r) {
            if (r.message) {
                var parent = page.main.find(".payment-table").empty();
                if (r.message.payments.length > 0) {
                    $(frappe.render_template('payment_export_table', r.message)).appendTo(parent);
                } else {
                    $('<h3>No payment entries to be paid found with status draft</h3>').appendTo(parent);
                }
            } 
        }
    });
}

