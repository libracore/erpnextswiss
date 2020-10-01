// Copyright (c) 2020, libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('HLK Structur Organisation Template', {
	refresh: function(frm) {
		frappe.call({
			"method": "erpnextswiss.erpnextswiss.page.bkp_importer.utils.get_item_group_for_structur_element_filter",
			"async": false,
			"callback": function(response) {
				var item_group_for_structur_element_filter = response.message;
				frm.fields_dict['hlk_structur_organisation'].grid.get_field('main_element').get_query = function(doc, cdt, cdn) {
					return {    
						filters:[
							['item_group', '=', item_group_for_structur_element_filter]
						]
					}
				};
				
				frm.fields_dict['hlk_structur_organisation'].grid.get_field('parent_element').get_query = function(doc, cdt, cdn) {
					return {    
						filters:[
							['item_group', '=', item_group_for_structur_element_filter]
						]
					}
				};
			}
		});
	}
});
