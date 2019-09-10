// Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inspection Equipment Transaction', {
	refresh: function(frm) {
		
	},
	current_status: function(frm) {
		if (frm.doc.current_status == 'Taken') {
			cur_frm.set_value('new_status', 'On Stock');
		} else {
			cur_frm.set_value('new_status', 'Taken');
		}
	}
});
