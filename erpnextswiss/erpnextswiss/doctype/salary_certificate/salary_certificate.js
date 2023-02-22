// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Certificate', {
	refresh: function(frm) {
        // add utility buttons
        frm.add_custom_button(__("Get values"), function() {
            if (frm.doc.name.startsWith("New")) {
                frappe.msgprint( __("Please save the record before populating it with data") );
            } else {
                frappe.call({
                    method: 'fetch_values',
                    doc: frm.doc,
                    callback: function(response) {
                        frm.refresh();
                                    
                        // show a short information
                        show_alert( __("Salary slip information collected"));
                    }
                }); 
            }
        });
        frm.add_custom_button(__("Calculate totals"), function() {
            // calculate gross salary
            var gross_salary = frm.doc.salary
                + frm.doc.catering
                + frm.doc.car
                + frm.doc.other_salary
                + frm.doc.irregular
                + frm.doc.capital
                + frm.doc.participation
                + frm.doc.board
                + frm.doc.other;
            
            // calculate net salary
            var net_salary = gross_salary 
                - frm.doc.deduction_ahv
                - frm.doc.deduction_pension
                - frm.doc.deduction_pension_additional;
                
            // assign to form
            cur_frm.set_value('gross_salary', gross_salary);
            cur_frm.set_value('net_salary', net_salary);    
            
            // show a short information
            show_alert( __("Totals have been updated"));
        });
	}
});
