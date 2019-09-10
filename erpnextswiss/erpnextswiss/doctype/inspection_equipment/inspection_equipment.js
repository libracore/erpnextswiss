// Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inspection Equipment', {
	refresh: function(frm) {
		if (!frm.doc.__islocal) {
		   frm.add_custom_button(__("Create Transaction"), function() {
				create_transaction(frm);
			});
		}
	}
});

function create_transaction(frm) {
	frappe.prompt([
		{'fieldname': 'employee', 'fieldtype': 'Link', 'label': 'Employee', 'reqd': 1, 'options': 'Employee'}  
	],
	function(values){
		frappe.call({
			method: "erpnextswiss.erpnextswiss.doctype.inspection_equipment.inspection_equipment.create_transaction",
			args:{
				'inspection_equipment': frm.doc.name,
				'employee': values.employee,
				'status': frm.doc.transaction_status
			},
			callback: function(r)
			{
				frappe.set_route("Form", "Inspection Equipment Transaction", r.message);
			}
		});
	},
	'Select an Employee for Transaction',
	'Create Transaction'
	);
}