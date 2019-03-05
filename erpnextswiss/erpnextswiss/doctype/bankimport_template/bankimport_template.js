// Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('BankImport Template', {
	refresh: function(frm) {
		// Set conditional required field
		console.log(frm.doc.valuta_field);
		if(frm.doc.transaction_hash == 0){
			frm.set_df_property("transaction_field",'reqd',1);
		}
	},
	before_save: function(frm) {
		if(frm.doc.remark_field == null){
			frm.set_value("remark_field",-1);
		}
		if(frm.doc.iban_field == null){
			frm.set_value("iban_field",-1);
		}
		if(frm.doc.bic_field == null){
			frm.set_value("bic_field",-1);
		}
		if(frm.doc.valuta_field == null){
			frm.set_value("valuta_field",-1);
		}
	},
	k_separator: function(frm) {
		if(frm.doc.k_separator && frm.doc.k_separator == frm.doc.decimal_separator){
			frm.set_value("k_separator","");
			frappe.throw(__("Selection invalid, cannot be same as decimal seperator"));
		}
	},
	decimal_separator: function(frm) {
		if(frm.doc.decimal_separator && frm.doc.decimal_separator == frm.doc.k_separator){
			frm.set_value("decimal_separator","");
			frappe.throw(__("Selection invalid, cannot be same as thousand seperator"));
		}
	},
	transaction_hash: function(frm) {
		frm.set_df_property("transaction_field",'reqd', frm.doc.transaction_hash == 0 ? 1 : 0);
		if(frm.doc.transaction_hash == 1){
			frm.set_value("transaction_field",undefined)
		}
	},
	advanced_settings: function(frm) {
		//Set thousand and decimal defaults
		if(frm.doc.advanced_settings == 0){
			frm.set_value("k_separator","");
			frm.set_value("decimal_separator","");
		}
	}/*,
	remark_field: function(frm) {
		if(frm.doc.remark_field == null){
			frm.set_value("remark_field",-1);
		}
	},
	iban_field: function(frm) {
		if(frm.doc.iban_field == null){
			frm.set_value("iban_field",-1);
		}
	},
	bic_field: function(frm) {
		if(frm.doc.bic_field == null){
			frm.set_value("bic_field",-1);
		}
	},
	valuta_field: function(frm) {
		console.log(frm.doc.valuta_field)
		if(frm.doc.valuta_field == null){
			frm.set_value("valuta_field",-1);
		}
	}
	*/
});
