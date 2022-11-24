// Copyright (c) 2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('VAT Declaration DE', {
    refresh: function(frm) {
        frm.add_custom_button(__("Get values"), function() 
        {
            get_values(frm);
        });
        frm.add_custom_button(__("Recalculate"), function() 
        {
            recalculate(frm);
        });
    },
    onload: function(frm) {
        if (frm.doc.__islocal) {
            // this function is called when a new VAT declaration is created
            // get current month (0..11)
            var d = new Date();
            var n = d.getMonth();
            // define title as Qn YYYY of the last complete quarter
            var title = " / " + d.getFullYear();
            if (frm.doc.interval === "Quarterly") {
                if ((n > (-1)) && (n < 3)) {
                    title = "Q4 / " + (d.getFullYear() - 1);
                    frm.set_value('start_date', (d.getFullYear() - 1) + "-10-01");
                    frm.set_value('end_date', (d.getFullYear() - 1) + "-12-31");
                } else if ((n > (2)) && (n < 6)) {
                    title = "Q1" + title;
                    frm.set_value('start_date', d.getFullYear() + "-01-01");
                    frm.set_value('end_date', d.getFullYear() + "-03-31");
                } else if ((n > (5)) && (n < 9)) {
                    title = "Q2" + title;
                    frm.set_value('start_date', d.getFullYear() + "-04-01");
                    frm.set_value('end_date', d.getFullYear() + "-06-30");
                } else {
                    title = "Q3" + title;
                    frm.set_value('start_date', d.getFullYear() + "-07-01");
                    frm.set_value('end_date', d.getFullYear() + "-09-30");
                } 
            } else {
                if (n === 0) {
                    title = "Dez / " + (d.getFullYear() - 1);
                    frm.set_value('start_date', (d.getFullYear() - 1) + "-12-01");
                    frm.set_value('end_date', (d.getFullYear() - 1) + "-12-31");
                } else {
                    var last_month = new Date(d.getFullYear(), n - 1, 1, 12, 0, 0);
                    var last_day_of_last_month = new Date(d.getFullYear(), n, 0, 12, 0, 0);
                    title = last_month.toLocaleString("de", {'month': 'short'}) + title;
                    frm.set_value('start_date', (last_month.toISOString().split('T')[0]));
                    frm.set_value('end_date', (last_day_of_last_month.toISOString().split('T')[0]));
                }
            }

            cur_frm.set_value('title', title + " - " + (frm.doc.cmp_abbr || ""));
        }
    },
    company: function(frm) {
        if ((frm.doc.__islocal) && (frm.doc.company)) {
            // replace company key
            var parts = frm.doc.title.split(" - ");
            if (parts.length > 1) {
                var new_title = [];
                for (var i = 0; i < (parts.length - 1); i++) {
                    new_title.push(parts[i]);
                }
                new_title.push(frm.doc.cmp_abbr);
                cur_frm.set_value("title", new_title.join(" - "));
            } else if (parts.length === 0) {
                // key missing
                cur_frm.set_value("title", frm.doc.title + " - " + frm.doc.cmp_abbr);
            }
            
        }
    }
});

// retrieve values from database
function get_values(frm) {
    // Revenues
    get_total(frm, "viewVAT_DE_81", 'amount_81');
    get_tax(frm, "viewVAT_DE_81", 'tax_81');
    get_total(frm, "viewVAT_DE_86", 'amount_86');
    get_tax(frm, "viewVAT_DE_86", 'tax_86');
    get_total(frm, "viewVAT_DE_35", 'amount_35');
    get_tax(frm, "viewVAT_DE_35", 'tax_35');
    get_total(frm, "viewVAT_DE_77", 'amount_77');
    get_tax(frm, "viewVAT_DE_77", 'tax_77');
    get_total(frm, "viewVAT_DE_76", 'amount_76');
    get_tax(frm, "viewVAT_DE_76", 'tax_76');
    // innercommunal revenue
    get_total(frm, "viewVAT_DE_41", 'amount_41');
    get_total(frm, "viewVAT_DE_44", 'amount_44');
    get_total(frm, "viewVAT_DE_49", 'amount_49');
    get_total(frm, "viewVAT_DE_43", 'amount_43');
    get_total(frm, "viewVAT_DE_48", 'amount_48');
    // innercommunal purchases
    get_total(frm, "viewVAT_DE_89", 'amount_89');
    get_tax(frm, "viewVAT_DE_89", 'tax_89');
    get_total(frm, "viewVAT_DE_93", 'amount_93');
    get_tax(frm, "viewVAT_DE_93", 'tax_93');
    get_total(frm, "viewVAT_DE_95", 'amount_95');
    get_tax(frm, "viewVAT_DE_95", 'tax_95');
    get_total(frm, "viewVAT_DE_94", 'amount_94');
    get_tax(frm, "viewVAT_DE_94", 'tax_94');
    get_total(frm, "viewVAT_DE_91", 'amount_91');
    // reverse charge
    get_total(frm, "viewVAT_DE_46", 'amount_46');
    get_tax(frm, "viewVAT_DE_46", 'tax_46');
    get_total(frm, "viewVAT_DE_73", 'amount_73');
    get_tax(frm, "viewVAT_DE_73", 'tax_73');
    get_total(frm, "viewVAT_DE_84", 'amount_84');
    get_tax(frm, "viewVAT_DE_84", 'tax_84');
    // additional revenue
    get_total(frm, "viewVAT_DE_42", 'amount_42');
    get_total(frm, "viewVAT_DE_60", 'amount_60');
    get_total(frm, "viewVAT_DE_21", 'amount_21');
    get_total(frm, "viewVAT_DE_45", 'amount_45');
    // pretax
    get_tax(frm, "viewVAT_DE_66", 'tax_66');
    get_tax(frm, "viewVAT_DE_61", 'tax_61');
    get_tax(frm, "viewVAT_DE_62", 'tax_62');
    get_tax(frm, "viewVAT_DE_67", 'tax_67');
    get_tax(frm, "viewVAT_DE_63", 'tax_63');
    get_tax(frm, "viewVAT_DE_59", 'tax_59');
    get_tax(frm, "viewVAT_DE_64", 'tax_64');
    // others
    get_tax(frm, "viewVAT_DE_65", 'tax_65');
    get_tax(frm, "viewVAT_DE_69", 'tax_69');
    get_tax(frm, "viewVAT_DE_39", 'tax_39');

    recalculate(frm);
}

// force recalculate
function recalculate(frm) {
    // set taxes
    var total_revenue_tax = cur_frm.doc.tax_81
        + cur_frm.doc.tax_86
        + cur_frm.doc.tax_35
        + cur_frm.doc.tax_77
        + cur_frm.doc.tax_76
        + cur_frm.doc.tax_89
        + cur_frm.doc.tax_93
        + cur_frm.doc.tax_95
        + cur_frm.doc.tax_94
        + cur_frm.doc.tax_46
        + cur_frm.doc.tax_73
        + cur_frm.doc.tax_84;
        
    var total_pretax = cur_frm.doc.tax_66
        + cur_frm.doc.tax_61
        + cur_frm.doc.tax_62
        + cur_frm.doc.tax_67
        + cur_frm.doc.tax_63
        + cur_frm.doc.tax_59
        + cur_frm.doc.tax_64;
    
    var preliminary_tax = total_revenue_tax - total_pretax;
    
    var tax_due = preliminary_tax - cur_frm.doc.tax_39;
    
    cur_frm.set_value('total_revenue_tax', total_revenue_tax);
    cur_frm.set_value('total_pretax', total_pretax);
    cur_frm.set_value('preliminary_tax', preliminary_tax);
    cur_frm.set_value('tax_due', tax_due);
}

/* view: view to use
 * target: target field
 */
function get_total(frm, view, target) {
    // total revenues is the sum of all base grand totals in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_view_total',
        args: { 
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date,
            view_name: view,
            company: frm.doc.company
        },
        async: false,
        freeze: true,
        freeze_message: __("Daten zusammentragen..."),
        callback: function(r) {
            if (r.message) {
                frm.set_value(target, r.message.total);
            }
        }
    }); 
}

/* view: view to use
 * target: target field
 */
function get_tax(frm, view, target) {
    // total tax is the sum of all taxes in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_view_tax',
        args: { 
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date,
            view_name: view,
            company: frm.doc.company
        },
        async: false,
        freeze: true,
        freeze_message: __("Daten zusammentragen..."),
        callback: function(r) {
            if (r.message) {
                frm.set_value(target, r.message.total);
            }
        }
    }); 
}
