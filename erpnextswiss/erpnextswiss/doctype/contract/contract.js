// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
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
	}
});
