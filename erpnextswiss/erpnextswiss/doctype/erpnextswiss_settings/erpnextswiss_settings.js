// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ERPNextSwiss Settings', {
	refresh: function(frm) {
        // filter intermediate_account
        cur_frm.fields_dict['intermediate_account'].get_query = function(doc) {
            return {
                filters: {
                    'account_type': 'Bank'
                }
            }
        }
	}
});
