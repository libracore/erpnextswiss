// Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ebics Statement', {
    refresh: function(frm) {
        check_display_bank_wizard(frm);
        prepare_defaults(frm);
    }
});

function check_display_bank_wizard(frm) {
    if (frm.doc.transactions) {
        for (let i = 0; i < frm.doc.transactions.length; i++) {
            if (frm.doc.transactions[i].status === "Pending") {
                frm.add_custom_button(__("Bank Wizard"), function() {
                    start_bank_wizard();
                });
                break;
            }
        }
    }
}

function prepare_defaults(frm) {
    locals.bank_wizard = {};
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_accounts',
        'args': {
            'bank_account': cur_frm.doc.account
        },
        'callback': function(r) {
            if (r.message) {
                locals.bank_wizard.payable_account = r.message.payable_account;
                locals.bank_wizard.receivable_account = r.message.receivable_account;
                locals.bank_wizard.expense_payable_account = r.message.expense_payable_account;
            } else {
                frappe.msgprint( __("Please set the <b>default accounts</b> in <a href=\"/desk#Form/Company/{0}\">{0}</a>.").replace("{0}", r.message.company) );
            }
        }
    });
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_customer',
        'callback': function(r) {
            if ((r.message) && (r.message.customer != "")) {
                locals.bank_wizard.default_customer = r.message.customer;
            } else {
                frappe.msgprint( __("Please set the <b>default customer</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
            }
        }
    }); 
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_supplier',
        'callback': function(r) {
            if ((r.message) && (r.message.supplier != "")) {
                locals.bank_wizard.default_supplier = r.message.supplier;
            } else {
                frappe.msgprint( __("Please set the <b>default supplier</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
            }
        }
    });
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_intermediate_account',
        'callback': function(r) {
            if ((r.message) && (r.message.account != "")) {
               locals.bank_wizard.intermediate_account = r.message.account;
            } else {
                frappe.msgprint( __("Please set the <b>intermediate bank account</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
            }
        }
    }); 
}

function start_bank_wizard() {
    // get pending transactions
    let pending_transactions = [];
    for (let i = 0; i < cur_frm.doc.transactions.length; i++) {
        if (cur_frm.doc.transactions[i].status === "Pending") {
            pending_transactions.push(cur_frm.doc.transactions[i]);
        }
    }
    
    if (pending_transactions.length > 0) {
        let transaction_content = frappe.render_template('transaction_table', {'transactions': pending_transactions});
        let d = new frappe.ui.Dialog({
            'fields': [
                {
                    'fieldname': 'transaction_table', 
                    'fieldtype': 'HTML', 
                    'label': __('Transactions'), 
                    'options': transaction_content
                },
            ],
            'primary_action': function(){
                d.hide();
                // and remove the old dialog (otherwise, it cannot be opened again without F5)
                clear_dialog_content();
            },
            'secondary_action': function() {
                clear_dialog_content();
            },
            'primary_action_label': __('Close'),
            'title': __('Bank Wizard')
        });
        d.no_cancel();
        d.show();
        
        setTimeout(function () {
            let modals = document.getElementsByClassName("modal-dialog");
            if (modals.length > 0) {
                modals[modals.length - 1].style.width = "1000px";
            }
            
            // wait for the dialog to be ready to attach handlers
            attach_button_handlers(pending_transactions);
        }, 300);
    }
}

function clear_dialog_content() {
    let modals = document.getElementsByClassName("modal-dialog");
    if (modals.length > 0) {
        modals[modals.length - 1].remove();
    }
}

function attach_button_handlers(transactions) {
    // attach button handlers
    var bank_account = cur_frm.doc.account;
    var company = cur_frm.doc.company;
    var intermediate_account = locals.bank_wizard.intermediate_account;
    var payable_account = locals.bank_wizard.payable_account;
    var expense_payable_account = locals.bank_wizard.payable_account;
    var receivable_account = locals.bank_wizard.receivable_account;
    var default_customer = locals.bank_wizard.default_customer;
    var default_supplier = locals.bank_wizard.default_supplier;
    transactions.forEach(function (transaction) {
        // add generic payables/receivables handler
        if (transaction.credit_debit == "DBIT") {
            // purchase invoice match
            var button = document.getElementById("btn-close-pinv-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
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
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // expense claim match
            var button = document.getElementById("btn-close-exp-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': expense_payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Employee",
                        'party': transaction.employee_match,
                        'references': transaction.expense_matches,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // supplier match
            var button = document.getElementById("btn-close-supplier-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Supplier",
                        'party': transaction.party_match,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // employee match
            var button = document.getElementById("btn-close-employee-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': expense_payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Employee",
                        'party': transaction.employee_match,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // payables
            var button = document.getElementById("btn-close-payable-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Supplier",
                        'party': default_supplier,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
        } else {
            // sales invoice match
            var button = document.getElementById("btn-close-sinv-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
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
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // customer match
            var button = document.getElementById("btn-close-customer-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': receivable_account,
                        'paid_to': bank_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': transaction.party_match,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // receivables
            var button = document.getElementById("btn-close-receivable-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': receivable_account,
                        'paid_to': bank_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': default_customer,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
        }
        // add intermediate account handler
        var button = document.getElementById("btn-close-intermediate-" + transaction.txid);
        if (button) {
            button.addEventListener("click", function(e) {
                e.target.disabled = true;
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
                    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                    'party_iban': transaction.party_iban,
                    'company': company
                }
                create_payment_entry(payment, transaction.txid);
            });
        }
    }); 
}

function create_payment_entry(payment, txid) {
    frappe.call({
        'method': "erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_payment_entry",
        'args': payment,
        'callback': function(r) {
            // open new record in a separate tab
            window.open(r.message.link, '_blank');
            close_entry(txid, r.message.payment_entry);
        }
    });    
}

function close_entry(txid, payment_entry) {
    // update transaction row
    for (let i = 0; i < cur_frm.doc.transactions.length; i++) {
        if (cur_frm.doc.transactions[i].txid === txid) {
            frappe.model.set_value(cur_frm.doc.transactions[i].doctype, cur_frm.doc.transactions[i].name, 'payment_entry', payment_entry);
            frappe.model.set_value(cur_frm.doc.transactions[i].doctype, cur_frm.doc.transactions[i].name, 'status', "Completed");
            break;
        }
    }
    cur_frm.save();
    // close the entry in the list
    let table_row = document.getElementById("row-transaction-" + txid);
    table_row.classList.add("hidden");  
}
