frappe.pages['bank_wizard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Bank Wizard'),
        single_column: true
    });

    frappe.bank_wizard.make(page);
    frappe.bank_wizard.run();
    
    // add the application reference
    frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.bank_wizard = {
    start: 0,
    make: function(page) {
        var me = frappe.bank_wizard;
        me.page = page;
        me.body = $('<div></div>').appendTo(me.page.main);
        var data = "";
        $(frappe.render_template('bank_wizard', data)).appendTo(me.body);
        
        // attach button handlers
        this.page.main.find(".btn-parse-file").on('click', function() {
            var me = frappe.bankimport;
            
            // get selected account
            var account = document.getElementById("bank_account").value;
            
            // read the file 
            var file = document.getElementById("input_file").files[0];
            var content = "";
            if (file) {
                // create a new reader instance
                var reader = new FileReader();
                // assign load event to process the file
                reader.onload = function (event) {
                    // enable waiting gif
                    frappe.bank_wizard.start_wait();
                    
                    // read file content
                    content = event.target.result;
                    

                    // call bankimport method with file content
                    frappe.call({
                        method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.read_camt053',
                        args: {
                            content: content,
                            account: account
                        },
                        callback: function(r) {
                            if (r.message) {
				frappe.show_alert( r.message.transactions.length +  __(" transactions found") );
                                frappe.bank_wizard.render_response(page, r.message);
                            } 
                        }
                    });
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
            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_bank_accounts',
            callback: function(r) {
                if (r.message) {
                    var select = document.getElementById("bank_account");
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
            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_intermediate_account',
            callback: function(r) {
                if ((r.message) && (r.message.account != "")) {
                    document.getElementById("intermediate_account").value = r.message.account;
                } else {
		    frappe.msgprint( __("Please set the <b>intermediate bank account</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
		}
            }
        }); 
        frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_payable_account',
            callback: function(r) {
                if ((r.message) && (r.message.account != "")) {
                    document.getElementById("payable_account").value = r.message.account;
		    
                } else {
		    frappe.msgprint( __("Please set the <b>default payable bank account</b> in the company.") );
		}
            }
        }); 
	frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_receivable_account',
            callback: function(r) {
                if ((r.message) && (r.message.account != "")) {
                    document.getElementById("receivable_account").value = r.message.account;
                } else {
		    frappe.msgprint( __("Please set the <b>default receivable bank account</b> in the company.") );
		}
            }
        }); 
	frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_customer',
            callback: function(r) {
                if ((r.message) && (r.message.customer != "")) {
                    document.getElementById("default_customer").value = r.message.customer;
                } else {
		    frappe.msgprint( __("Please set the <b>default customer</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
		}
            }
        }); 
	frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_supplier',
            callback: function(r) {
                if ((r.message) && (r.message.supplier != "")) {
                    document.getElementById("default_supplier").value = r.message.supplier;
                } else {
		    frappe.msgprint( __("Please set the <b>default supplier</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
		}
            }
        }); 
    },
    start_wait: function() {
	document.getElementById("waitingScreen").classList.remove("hidden");
	document.getElementById("btn-parse-file").classList.add("disabled");
    },
    end_wait: function() {
	document.getElementById("waitingScreen").classList.add("hidden");
	document.getElementById("btn-parse-file").classList.remove("disabled");
    },
    render_response: function(page, message) {
        // disable waiting gif
        frappe.bank_wizard.end_wait();
    
        // display the transactions as table
        var container = document.getElementById("table_placeholder");
        var content = frappe.render_template('transaction_table', message);
        container.innerHTML = content;
    
        // attach button handlers
        var bank_account = document.getElementById("bank_account").value;
        var intermediate_account = document.getElementById("intermediate_account").value;
        var payable_account = document.getElementById("payable_account").value;
        var receivable_account = document.getElementById("receivable_account").value;
        var default_customer = document.getElementById("default_customer").value;
        var default_supplier = document.getElementById("default_supplier").value;
        message.transactions.forEach(function (transaction) {
	    // add generic payables/receivables handler
	    if (transaction.credit_debit == "DBIT") {
		// purchase invoice match
		var button = document.getElementById("btn-close-pinv-" + transaction.txid);
		if (button) {
		    button.addEventListener("click", function() {
			var payment = {
			    'amount': transaction.amount,
			    'date': transaction.date,
			    'paid_from': bank_account,
			    'paid_to': payable_account,
			    'reference_no': transaction.unique_reference,
			    'type': "Pay",
			    'party_type': "Supplier",
			    'party': transaction.party_match,
			    'references': transaction.invoice_matches,
			    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
			}
			frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		    });
		}
		// supplier match
		var button = document.getElementById("btn-close-supplier-" + transaction.txid);
		if (button) {
		    button.addEventListener("click", function() {
			var payment = {
			    'amount': transaction.amount,
			    'date': transaction.date,
			    'paid_from': bank_account,
			    'paid_to': payable_account,
			    'reference_no': transaction.unique_reference,
			    'type': "Pay",
			    'party_type': "Supplier",
			    'party': transaction.party_match,
			    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
			}
			frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		    });
		}
		// payables
		var button = document.getElementById("btn-close-payable-" + transaction.txid);
		if (button) {
		    button.addEventListener("click", function() {
			var payment = {
			    'amount': transaction.amount,
			    'date': transaction.date,
			    'paid_from': bank_account,
			    'paid_to': payable_account,
			    'reference_no': transaction.unique_reference,
			    'type': "Pay",
			    'party_type': "Supplier",
			    'party': default_supplier,
			    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
			}
			frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		    });
		}
	    } else {
		// sales invoice match
		var button = document.getElementById("btn-close-sinv-" + transaction.txid);
		if (button) {
		    button.addEventListener("click", function() {
			var payment = {
			    'amount': transaction.amount,
			    'date': transaction.date,
			    'paid_from': receivable_account,
			    'paid_to': bank_account,
			    'reference_no': transaction.unique_reference,
			    'type': "Receive",
			    'party_type': "Customer",
			    'party': transaction.party_match,
			    'references': transaction.invoice_matches,
			    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
			}
			frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		    });
		}
		// customer match
		var button = document.getElementById("btn-close-customer-" + transaction.txid);
		if (button) {
		    button.addEventListener("click", function() {
			var payment = {
			    'amount': transaction.amount,
			    'date': transaction.date,
			    'paid_from': receivable_account,
			    'paid_to': bank_account,
			    'reference_no': transaction.unique_reference,
			    'type': "Receive",
			    'party_type': "Customer",
			    'party': transaction.party_match,
			    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
			}
			frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		    });
		}
		// receivables
		var button = document.getElementById("btn-close-receivable-" + transaction.txid);
		if (button) {
		    button.addEventListener("click", function() {
			var payment = {
			    'amount': transaction.amount,
			    'date': transaction.date,
			    'paid_from': receivable_account,
			    'paid_to': bank_account,
			    'reference_no': transaction.unique_reference,
			    'type': "Receive",
			    'party_type': "Customer",
			    'party': default_customer,
			    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
			}
			frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		    });
		}		
	    }
	    // add intermediate account handler
            var button = document.getElementById("btn-close-intermediate-" + transaction.txid);
	    if (button) {
		button.addEventListener("click", function() {
		    var paid_to = bank_account;
		    var paid_from = intermediate_account;
		    if (transaction.credit_debit == "DBIT") {
			paid_from = bank_account;
			paid_to = intermediate_account;
		    }
		    // note: currency is defined through account currencies of the bank account
		    var payment = {
			'amount': transaction.amount,
			'date': transaction.date,
			'paid_from': paid_from,
			'paid_to': paid_to,
			'reference_no': transaction.unique_reference,
			'type': "Internal Transfer",
			'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address)
		    }
		    frappe.bank_wizard.create_payment_entry(payment, transaction.txid);
		});
	    }
        }); 
    },
    create_payment_entry: function(payment, txid) {
	//console.log(payment.toSource());
        frappe.call({
            method: "erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_payment_entry",
            args: payment,
            callback: function(r)
            {
                // open new record in a separate tab
		window.open('/desk#Form/Payment Entry/' + r.message, '_blank');
		// close the entry in the list
		var table_row = document.getElementById("row-transaction-" + txid);
		table_row.classList.add("hidden");
            }
        });    
    }
}
