frappe.pages['bankimport'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Bank import'),
		single_column: true
	});

	frappe.bankimport.make(page);
	frappe.bankimport.run();
	
	// add the application reference
	frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.bankimport = {
	start: 0,
	make: function(page) {
		var me = frappe.bankimport;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('bankimport', data)).appendTo(me.body);

		// add menu button
		this.page.add_menu_item(__("Match payments"), function() {
			// navigate to bank import tool
			window.location.href="/app/match_payments";
		});
		this.page.add_menu_item(__("Debug Template"), function() {
			// navigate to bank import tool
			$('.btn-parse-file').trigger('click', [true]);
		});

		// attach button handlers
		this.page.main.find(".btn-parse-file").on('click', function(event, debug=false) {
			
			var me = frappe.bankimport;
			
			// get selected bank
			var bank = document.getElementById("bank").value;
			// get selected account
			var account = document.getElementById("payment_account").value;
			// get selected option
			//var auto_submit = document.getElementById("auto_submit").checked;
			var auto_submit = false;
			// get format type
			var format = document.getElementById("format").value;
			
			// read the file 
			var file = document.getElementById("input_file").files[0];
			var content = "";
			if (file) {
				// create a new reader instance
				var reader = new FileReader();
				// assign load event to process the file
				reader.onload = function (event) {
					// enable waiting gif
					frappe.bankimport.start_wait();
					
					// read file content
					content = String.fromCharCode.apply(null, Array.prototype.slice.apply(new Uint8Array(event.target.result)));
					//content = event.target.result;
					
					if (format == "csv") {
						// call bankimport method with file content
						frappe.call({
							method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.parse_file',
							args: {
								content: content,
								bank: bank,
								account: account,
								auto_submit: auto_submit,
								debug : debug
							},
							callback: function(r) {
								if (r.message) {
									frappe.bankimport.render_response(page, r.message);
								} 
							}
						}); 
					} 
					else if (format == "camt054") {
						// call bankimport method with file content
						frappe.call({
							method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.read_camt054',
							args: {
								content: content,
								bank: bank,
								account: account,
								auto_submit: auto_submit
							},
							callback: function(r) {
								if (r.message) {
									frappe.bankimport.render_response(page, r.message);
								} 
							}
						});
					}
					else if (format == "camt053") {
						// call bankimport method with file content
						frappe.call({
							method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.read_camt053',
							args: {
								content: content,
								bank: bank,
								account: account,
								auto_submit: auto_submit
							},
							callback: function(r) {
								if (r.message) {
									frappe.bankimport.render_response(page, r.message);
								} 
							}
						});
					} else {
						frappe.msgprint("Unknown format. Please contact your system manager");
					}
				}
				// assign an error handler event
				reader.onerror = function (event) {
					frappe.msgprint(__("Error reading file"), __("Error"));
				}
				reader.readAsArrayBuffer(file);
				//reader.readAsText(file, "ANSI");
			}
			else
			{
				frappe.msgprint(__("Please select a file."), __("Information"));
			}
			
		});
	},
	run: function() {
		// populate bank accounts
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.get_bank_accounts',
			args: { },
			callback: function(r) {
				if (r.message) {
					var select = document.getElementById("payment_account");
					for (var i = 0; i < r.message.accounts.length; i++) {
						var opt = document.createElement("option");
						opt.value = r.message.accounts[i];
						opt.innerHTML = r.message.accounts[i];
						select.appendChild(opt);
					}
				}
			}
		});
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.get_bank_settings',
			args: { },
			callback: function(r) {
				if (r.message.banks) {
					var select = document.getElementById("bank");
					// Change format selection based on bank setting information
					select.onchange = function() {
						frappe.bankimport.change_option("format",r.message.banks[select.selectedIndex].file_format.split('(').pop().split(')')[0]);
					}
					// Build enabled banks for import
					for (var i = 0; i < r.message.banks.length; i++) {
						var opt = document.createElement("option");
						if(r.message.banks[i].legacy_ref){
							opt.value = r.message.banks[i].legacy_ref;
						}else{
							opt.value = r.message.banks[i].bank_name;
						}
						//opt.setAttribute("importType",r.message.banks[i].filetype);
						opt.innerHTML = r.message.banks[i].bank_name;
						select.appendChild(opt);
					}
					// Build import formats based on doctype "
					/*
					var formatOption = document.getElementById("format");
					for (var i = 0; i < r.message.formats.length; i++) {
						var opt = document.createElement("option");
						opt.value = r.message.formats[i].format_ref;
						opt.innerHTML = __(r.message.formats[i].format_name);
						formatOption.appendChild(opt);
					}
					*/
					frappe.bankimport.change_option("format",r.message.banks[0].file_format.split('(').pop().split(')')[0])
				}
			}
		}); 
	},
	start_wait: function() {
		//document.getElementById("waitingScreen").style.display = "block";
	},
	end_wait: function() {
		document.getElementById("waitingScreen").style.display = "none";
	},
	render_response: function(page, message) {
		// disable waiting gif
		frappe.bankimport.end_wait();
		var parent = page.main.find(".insert-log-messages").empty();
		$('<p>' + __(message.message) + '</p>').appendTo(parent);
		frappe.msgprint(__(message.message));
		if (message.records) {
			for (var i = 0; i < message.records.length; i++) {
				$('<p><a href="/app/payment-entry/'
				  + message.records[i] + '">' 
				  + message.records[i] + '</a></p>').appendTo(parent);
			}
		}
	},
	change_option: function(id, valueToSelect) {
		var element = document.getElementById(id);
		element.value = valueToSelect;
	}
}
