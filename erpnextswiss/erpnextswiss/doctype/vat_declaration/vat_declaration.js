// Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('VAT Declaration', {
    refresh: function(frm) {
        frm.add_custom_button(__("Get values"), function() 
        {
            get_values(frm);
        });
        frm.add_custom_button(__("Recalculate"), function() 
        {
            recalculate(frm);
        });
        
        update_taxable_revenue(frm);
        update_tax_amounts(frm);
        update_payable_tax(frm);
    },
    onload: function(frm) {
        if (frm.doc.__islocal) {
            // this function is called when a new VAT declaration is created
            // get current month (0..11)
            var d = new Date();
            var n = d.getMonth();
            // define title as Qn YYYY of the last complete quarter
            var title = " / " + d.getFullYear();
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
    // Total revenue
    get_total(frm, "viewVAT_200", 'total_revenue');
    // get_total(frm, "viewVAT_205", 'non_taxable_revenue');
    // Deductions
    get_total(frm, "viewVAT_220", 'tax_free_services');
    get_total(frm, "viewVAT_221", 'revenue_abroad');
    get_total(frm, "viewVAT_225", 'transfers');
    get_total(frm, "viewVAT_230", 'non_taxable_services');
    get_total(frm, "viewVAT_235", 'losses');
    // Tax calculation
    if (frm.doc.vat_type == "effective") {
        get_total(frm, "viewVAT_302", 'normal_amount');
        get_total(frm, "viewVAT_312", 'reduced_amount');
        get_total(frm, "viewVAT_342", 'lodging_amount');
    }
    else {
        get_total(frm, "viewVAT_322", 'amount_1');
        get_total(frm, "viewVAT_332", 'amount_2');
    }
    get_total(frm, "viewVAT_382", 'additional_amount');
    get_tax(frm, "viewVAT_382", 'additional_tax');
    // Pretaxes
    if (frm.doc.vat_type == "effective") {
        get_tax(frm, "viewVAT_400", 'pretax_material');
        get_tax(frm, "viewVAT_405", 'pretax_investments');
    }
}

// force recalculate
function recalculate(frm) {
    update_taxable_revenue(frm);
    update_tax_amounts(frm);
    update_payable_tax(frm);
}

// add change handlers for tax positions
frappe.ui.form.on("VAT Declaration", "normal_amount", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "reduced_amount", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "lodging_amount", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "additional_amount", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "amount_1", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "amount_2", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "rate_1", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "rate_2", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "normal_rate", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "reduced_rate", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "lodging_rate", function(frm) { update_tax_amounts(frm) } );
frappe.ui.form.on("VAT Declaration", "additional_tax", function(frm) { update_tax_amounts(frm) } );

function update_tax_amounts(frm) {
    // effective tax: tax rate on net amount
    var normal_tax = frm.doc.normal_amount * (frm.doc.normal_rate / 100);
    var reduced_tax = frm.doc.reduced_amount * (frm.doc.reduced_rate / 100);
    var lodging_tax = frm.doc.lodging_amount * (frm.doc.lodging_rate / 100);
    // saldo tax: rate on gross amount
    var tax_1 = frm.doc.amount_1  * (frm.doc.rate_1 / 100);
    var tax_2 = frm.doc.amount_2 * (frm.doc.rate_2 / 100);
    var total_tax = normal_tax + reduced_tax + lodging_tax + tax_1 + tax_2 + frm.doc.additional_tax;
    frm.set_value('normal_tax', normal_tax);
    frm.set_value('reduced_tax', reduced_tax);
    frm.set_value('lodging_tax', lodging_tax);
    frm.set_value('tax_1', tax_1);
    frm.set_value('tax_2', tax_2);
    frm.set_value('total_tax', total_tax);
}

// add change handlers for deduction positions
frappe.ui.form.on("VAT Declaration", "tax_free_services", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "revenue_abroad", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "transfers", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "non-taxable_services", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "losses", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "misc", function(frm) { update_taxable_revenue(frm) } );

function update_taxable_revenue(frm) {
    var deductions =  frm.doc.tax_free_services +
        frm.doc.revenue_abroad +
        frm.doc.transfers + 
        frm.doc.non_taxable_services + 
        frm.doc.losses +
        frm.doc.misc;
    var taxable = frm.doc.total_revenue - frm.doc.non_taxable_revenue - deductions;
    frm.set_value('total_deductions', deductions);
    frm.set_value('taxable_revenue', taxable);
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
        callback: function(r) {
            if (r.message) {
                frm.set_value(target, r.message.total);
            }
        }
    }); 
}

// add change handlers for pretax
frappe.ui.form.on("VAT Declaration", "pretax_material", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_investments", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "missing_pretax", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_correction_mixed", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_correction_other", function(frm) { update_payable_tax(frm) } );
        
function update_payable_tax(frm) {
    var pretax = frm.doc.pretax_material 
        + frm.doc.pretax_investments 
        + frm.doc.missing_pretax 
        - frm.doc.pretax_correction_mixed
        - frm.doc.pretax_correction_other
        + frm.doc.form_1050
        + frm.doc.form_1055;
    frm.set_value('total_pretax_reductions', pretax);
    var payable_tax = frm.doc.total_tax - pretax;
    frm.set_value('payable_tax', payable_tax);
}
