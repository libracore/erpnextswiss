// Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('VAT Declaration', {
    'refresh': function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Get values"), function() 
            {
                call_and_refresh(frm, 'get_values');
            });
            frm.add_custom_button(__("Recalculate"), function() 
            {
                recalculate(frm);
            });
        }
        else if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Download Transfer File"), function() 
            {
                download_transfer_file(frm);
            }).addClass("btn-primary");
        }
    },
    'onload': function(frm) {
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
    'company': function(frm) {
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

// fields that affect calculated values
[
    'total_revenue', 'non_taxable_revenue', 'tax_free_services', 'revenue_abroad', 'transfers',
    'non_taxable_services', 'losses', 'misc',
    'normal_amount_2024', 'reduced_amount_2024', 'lodging_amount_2024', 'normal_amount', 'reduced_amount', 'lodging_amount',
    'normal_rate_2024', 'reduced_rate_2024', 'lodging_rate_2024', 'normal_rate', 'reduced_rate', 'lodging_rate',
    'amount_1_2024', 'amount_2_2024', 'amount_1', 'amount_2', 'rate_1_2024', 'rate_2_2024', 'rate_1', 'rate_2',
    'additional_amount_2024', 'additional_amount', 'additional_tax_2024', 'additional_tax',
    'pretax_material', 'pretax_investments', 'missing_pretax', 'pretax_correction_mixed', 'pretax_correction_other',
    'form_1050', 'form_1055', 'vat_type', 'start_date'
].forEach(function(field) {
    frappe.ui.form.on('VAT Declaration', field, recalculate);
});

['VAT Declaration Activity', 'VAT Declaration Acquisition Tax'].forEach(function(doctype) {
    frappe.ui.form.on(doctype, {
        'turnover': recalculate,
        'rate': recalculate,
        'activities_remove': recalculate,
        'acquisition_taxes_remove': recalculate
    });
});

function recalculate(frm) {
    call_and_refresh(frm, 'calculate');
}

function call_and_refresh(frm, method) {
    frm.call(method).then(function() {
        frm.refresh_fields();
        frm.dirty();
    });
}

function download_transfer_file(frm) {
    frappe.call({
        'method': 'create_transfer_file',
        'doc': frm.doc,
        'callback': function(r) {
            if (r.message) {
                // prepare the xml file for download
                download("estv.xml", r.message.content);
            } 
        }
     });   
}

function download(filename, content) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}
