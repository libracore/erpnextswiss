// Copyright (c) 2018-2026, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Contract', {
	refresh: function(frm) {
        // filters
        // only allow active customers to be selected 
        // NOTE: customer queries are not applicable (ERPNext issue #15876)
        cur_frm.fields_dict['customer'].get_query = function(doc) {
            return {
                filters: { 'disabled': 0 }
            }
        }
        // only allow valid sales invoices to be linkes
        cur_frm.fields_dict['periods'].grid.get_field('invoice').get_query = function() {
            return {
                filters: { 'docstatus': 1 }
            }
        }
        if (frm.doc.enabled && frm.doc.has_pending_final_period) {
            frm.dashboard.add_indicator(
                __('Pending Final Invoice: {0} Days Remaining', [frm.doc.unbilled_days_remaining]),
                'orange'
            );
        }
	},
    before_save: function(frm) {
        if (frm.doc.__islocal) {
            set_next_date(frm);
        }
    },
    frequency: function(frm) {
        set_next_date(frm);
    }

});

function set_next_date(frm) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.contract.contract.get_next_date',
        'args': {
            'doc': frm.doc
        },
        'callback': function(response) {
            if (response.message) {
                cur_frm.set_value('next_invoice_date', response.message);
                cur_frm.set_value('set_invoice_date_manually', 0);
            }
        }
    });
}