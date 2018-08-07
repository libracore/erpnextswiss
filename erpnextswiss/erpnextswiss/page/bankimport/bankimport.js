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
            window.location.href="/desk#match_payments";
		});
        
		// attach button handlers
		this.page.main.find(".btn-parse-file").on('click', function() {
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
					content = event.target.result;
                    
                    if (format == "csv") {
                        // call bankimport method with file content
                        frappe.call({
                            method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.parse_file',
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
				
                reader.readAsText(file, "ANSI");
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
	},
    start_wait: function() {
        document.getElementById("waitingScreen").style.display = "block";
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
                $('<p><a href="/desk#Form/Payment Entry/'
                  + message.records[i] + '">' 
                  + message.records[i] + '</a></p>').appendTo(parent);
            }
        }
    }
}
