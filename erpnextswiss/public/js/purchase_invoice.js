frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        if (frm.doc.__islocal) {
			frm.add_custom_button(__("Scan Invoice Code Line"), function() {
				scan_invoice_code_line(frm);
			});
		}
    }
});

function scan_invoice_code_line(frm) {
	frappe.call({
        "method": "erpnextswiss.scripts.esr_qr_tools.get_default_item",
        "callback": function(response) {
            if (response.message.error) {
                frappe.msgprint(response.message.error);
            } else {
                var item = response.message.default_item;
                frappe.prompt([
                    {'fieldname': 'default_item', 'fieldtype': 'Link', 'label': __('Item'), 'reqd': 1, 'options': 'Item', 'default': item},
                    {'fieldname': 'code_scan', 'fieldtype': 'Code', 'label': __('Code'), 'reqd': 1}  
                ],
                function(values){
                    check_scan_input(frm, values.code_scan, values.default_item);
                },
                __('Scan Invoice Code Line'),
                __('OK')
                )
            }
        }
    });
}

function check_scan_input(frm, code_scan, default_item) {
	// ESR Section
	var regex = /[0-9]{13}[>][0-9]{27}[+][ ][0-9]{9}[>]/g; // 0100003949753>120000000000234478943216899+ 010001628>
	if (regex.test(code_scan) === true){
		var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
		var amount_int = parseInt(code_scan.split(">")[0].substring(2,10));
		var amount_dec = parseInt(code_scan.split(">")[0].substring(10,12));
		var amount = String(amount_int) + "." + String(amount_dec); // Betrag in CHF; z.B. 3949.75
		var reference = code_scan.split(">")[1].substring(0,27); // ESR-Referenznummer; z.B. 120000000000234478943216899
		var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
		get_data_based_on_esr(frm, participant, reference, amount, default_item);
	} else {
		// QR Section (tbd)
		frappe.msgprint(__("Invalid ESR Code Line"));
	}
}

function get_data_based_on_esr(frm, participant, reference, amount, default_item) {
	frappe.call({
        "method": "erpnextswiss.scripts.esr_qr_tools.get_data_based_on_esr",
        "args": {
            "participant": participant
        },
        "callback": function(response) {
            var error = response.message.error;
			if (!error) {
				var more_than_one_supplier = response.message.more_than_one_supplier;
				if (!more_than_one_supplier) {
					// exatly one supplier
					var supplier = response.message.supplier;
					// set fetched values
					cur_frm.set_value("supplier", supplier);
					cur_frm.set_value("payment_type", 'ESR');
					cur_frm.set_value("esr_reference_number", reference);
					
					// remove all item rows
					var tbl = frm.doc.items || [];
					var i = tbl.length;
					while (i--)
					{
						cur_frm.get_field("items").grid.grid_rows[i].remove();
					}
					
					// add row to item with amount of code line
					var child = cur_frm.add_child('items');
					frappe.model.set_value(child.doctype, child.name, 'item_code', default_item);
					frappe.model.set_value(child.doctype, child.name, 'qty', '1');
					frappe.model.set_value(child.doctype, child.name, 'rate', amount);
					cur_frm.refresh_field('items');
					setTimeout(function(){
						cur_frm.doc.items.forEach(function(entry) {
							entry.qty = 1.000;
							entry.rate = amount;
						});
						cur_frm.refresh_field('items');
					}, 2000);
				} else {
					// more than one supplier
					var _suppliers = response.message.supplier;
					var suppliers = [];
					for (var i = 0; i < _suppliers.length; i++) {
						suppliers.push(_suppliers[i]["supplier_name"] + " // (" + _suppliers[i]["name"] + ")");
					}
					suppliers = suppliers.join('\n');
					select_supplier(frm, suppliers, reference, amount, default_item);
				}
			} else {
				frappe.msgprint(__(error));
			}
        }
    });
}

function select_supplier(frm, suppliers, reference, amount, default_item) {
	frappe.prompt([
		{'fieldname': 'supplier', 'fieldtype': 'Select', 'label': __('Supplier'), 'reqd': 1, 'options': suppliers}  
	],
	function(values){
		var supplier = values.supplier.split(" // (")[1].replace(")", "");
		// set fetched values
		cur_frm.set_value("supplier", supplier);
		cur_frm.set_value("payment_type", 'ESR');
		cur_frm.set_value("esr_reference_number", reference);
		
		// remove all item rows
		var tbl = frm.doc.items || [];
		var i = tbl.length;
		while (i--)
		{
			cur_frm.get_field("items").grid.grid_rows[i].remove();
		}
		
		// add row to item with amount of code line
		var child = cur_frm.add_child('items');
		frappe.model.set_value(child.doctype, child.name, 'item_code', default_item);
		frappe.model.set_value(child.doctype, child.name, 'qty', 1.000);
		frappe.model.set_value(child.doctype, child.name, 'rate', amount);
		cur_frm.refresh_field('items');
		setTimeout(function(){
			cur_frm.doc.items.forEach(function(entry) {
				entry.qty = 1.000;
				entry.rate = amount;
			});
			cur_frm.refresh_field('items');
		}, 2000);
	},
	__('Choose Supplier'),
	__('Process')
	)
}

function get_data_based_on_qr(frm) {
	// tbd
}
