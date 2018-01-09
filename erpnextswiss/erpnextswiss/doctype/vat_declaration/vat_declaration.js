// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
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
        update_payable_tax(frm);
	}
});

// retrieve values from database
function get_values(frm) {
    get_total_revenue(frm);
    get_revenue(frm, "abroad_tax_template", 'revenue_abroad');
    if (frm.doc.vat_type == "effective") {
        get_revenue(frm, "normal_rate_tax_template", 'normal_amount');
        get_revenue(frm, "reduced_rate_tax_template", 'reduced_amount');
        get_revenue(frm, "lodging_rate_tax_template", 'lodging_amount');
        get_revenue(frm, "tax_free_tax_template", 'tax_free_services');
    }
    else {
        get_revenue(frm, "rate_1_tax_template", 'amount_1');
        get_revenue(frm, "rate_2_tax_template", 'amount_2');
    }
        
    if (frm.doc.vat_type == "effective") {
        get_pretax(frm);
    }
}

// force recalculate
function recalculate(frm) {
    update_tax_amounts(frm);
    update_payable_tax(frm);
}

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
        frm.set_value('start_date', (d.getFullYear() - 1) + "-10-01");
        frm.set_value('end_date', (d.getFullYear() - 1) + "-12-31");
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
    normal_tax = frm.doc.normal_amount * (frm.doc.normal_rate / 100);
    reduced_tax = frm.doc.reduced_amount * (frm.doc.reduced_rate / 100);
    lodging_tax = frm.doc.lodging_amount * (frm.doc.lodging_rate / 100);
    tax_1 = frm.doc.amount_1 * (frm.doc.rate_1 / 100);
    tax_2 = frm.doc.amount_2 * (frm.doc.rate_2 / 100);
    total_tax = normal_tax + reduced_tax + lodging_tax + tax_1 + tax_2 + frm.doc.additional_tax;
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

// get revenues
function get_total_revenue(frm) {
    // total revenues is the sum of all sales invoices in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_revenue',
        args: { 
            'start_date': frm.doc.start_date,
            'end_date': frm.doc.end_date
            },
        callback: function(r) {
            if (r.message) {
                // window.alert("got value: " + r.message.revenue.toSource() + " - " + r.message.revenue[0].total_revenue);
                frm.set_value('total_revenue', r.message.revenue);
            }
        }
    });
}

// template: template configuration field (VAT config)
// target: target fields
function get_revenue(frm, template, target) {
    // total revenues is the sum of all sales invoices in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_revenue',
        args: { 
            'start_date': frm.doc.start_date,
            'end_date': frm.doc.end_date,
            'tax_mode': template
            },
        callback: function(r) {
            if (r.message) {
                // window.alert("got value: " + r.message.revenue.toSource() + " - " + r.message.revenue[0].total_revenue);
                //frm.set_value(target, r.message.revenue[0].total_revenue);
                frm.set_value(target, r.message.revenue);
            }
        }
    }); 
}

function get_pretax(frm) {
    // total pretax  is the sum of the taxes collected in the tax collection account from payment invoices in the period    
    if (frm.doc.vat_type == "effective") {
        frappe.call({
            method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_pretax',
            args: { 
                'start_date': frm.doc.start_date,
                'end_date': frm.doc.end_date,
                },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('pretax_material', r.message.pretax);
                }
            }
        }); 
    } else {
        frm.set_value('pretax_material', 0.0);
    }
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
