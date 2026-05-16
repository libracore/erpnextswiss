// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Certificate', {
	refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Drucken"), function() {
                frappe.set_route("print", frm.doctype, frm.docname);
            }, __("Ausgabe"));

            frm.add_custom_button(__("PDF"), function() {
                var print_format = frm.meta.default_print_format || "605.040.18N Form. 11";
                var url = "/api/method/frappe.utils.print_format.download_pdf"
                    + "?doctype=" + encodeURIComponent(frm.doctype)
                    + "&name=" + encodeURIComponent(frm.docname)
                    + "&format=" + encodeURIComponent(print_format)
                    + "&no_letterhead=1";
                window.open(url, "_blank");
            }, __("Ausgabe"));
        }

        frm.add_custom_button(__("Werte holen"), function() {
            if (frm.is_new()) {
                frappe.msgprint(__("Bitte speichern Sie den Lohnausweis, bevor Werte geholt werden."));
            } else {
                frappe.call({
                    method: 'fetch_values',
                    doc: frm.doc,
                    callback: function(response) {
                        frm.refresh();
                                    
                        // show a short information
                        show_alert(__("Lohnwerte wurden geholt."));
                    }
                }); 
            }
        });
        frm.add_custom_button(__("Summen berechnen"), function() {
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
            show_alert(__("Summen wurden aktualisiert."));
        });
	}
});
