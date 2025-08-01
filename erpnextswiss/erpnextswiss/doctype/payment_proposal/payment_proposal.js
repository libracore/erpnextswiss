// Copyright (c) 2018-2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Proposal', {
     refresh: function(frm) {
        if (frm.doc.docstatus == 1) {
            // add download pain.001 button on submitted record
            frm.add_custom_button(__("Download bank file"), function() {
                generate_bank_file(frm);
            }).addClass("btn-primary");
            frm.add_custom_button(__("Download Wise file"), function() {
                generate_wise_file(frm);
            });
            // check if this account has an active ebic connection
            frappe.call({
                'method': 'has_active_ebics_connection',
                'doc': frm.doc,
                'callback': function(response) {
                    if (response.message.toString() !== "0") {
                        locals.ebics_connection = response.message[0]['name'];
                        frm.add_custom_button(__("Transmit by ebics"), function() {
                            transmit_ebics(frm);
                        }).addClass("btn-success");
                    }
                }
            });
        } else if (frm.doc.docstatus == 0) {
             // add set payment date
             frm.add_custom_button(__("Set Payment Date"), function() {
                  set_payment_date(frm);
             });
        }
        // filter for bank account
        cur_frm.fields_dict['pay_from_account'].get_query = function(doc) {
            return {
                filters: {
                    "account_type": "Bank",
                    "company": frm.doc.company
                }
            }
        }
        cur_frm.fields_dict['intermediate_account'].get_query = function(doc) {
            return {
                filters: {
                    "account_type": "Bank",
                    "company": frm.doc.company
                }
            }
        }
        // remove add grid buttons
        var grid_add_btns = document.getElementsByClassName("grid-add-row") || [];
        for (var b = 0; b < grid_add_btns.length; b++) {
            grid_add_btns[b].style.visibility = "Hidden";
        }
     },
     validate: function(frm) {
        if (frm.doc.pay_from_account == null) {
            frappe.msgprint( __("Please select an account to pay from.") );
            frappe.validated = false;
        }
        if ((frm.doc.use_intermediate == 1) && (frm.doc.intermediate_account == null)) {
            frappe.msgprint( __("Please select an intermediate account.") );
            frappe.validated = false;
        }
     }
});

function generate_bank_file(frm) {
     console.log("creating file...");
     frappe.call({
          'method': 'create_bank_file',
          'doc': frm.doc,
          'callback': function(r) {
               if (r.message) {
                    // prepare the xml file for download
                    download("payments.xml", r.message.content);
               } 
          }
     });     
}

function generate_wise_file(frm) {
     frappe.call({
          'method': 'create_wise_file',
          'doc': frm.doc,
          'callback': function(r) {
               if (r.message) {
                    // prepare the xml file for download
                    download("wise_payments.csv", r.message.content);
               } 
          }
     });     
}

function download(filename, content) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}

function set_payment_date(frm) {
    var d = new Date();
    d = new Date(d.setDate(d.getDate() + 1));
    frappe.prompt([
            {'fieldname': 'date', 'fieldtype': 'Date', 'label': __('Execute Payments On'), 'reqd': 1, 'default': d}  
        ],
        function(values){
            // loop through purchase invoices and set skonto date (this will be the execution date)
            var items = cur_frm.doc.purchase_invoices;
            items.forEach(function(entry) {
                frappe.model.set_value(entry.doctype, entry.name, 'skonto_date', values.date);
            });
            // set execution date
            cur_frm.set_value('date', values.date);
        },
        __('Execution Date'),
        __('Set')
    );
}

frappe.ui.form.on('Payment Proposal Purchase Invoice', {
    purchase_invoices_remove: function(frm) {
        recalculate_total(frm);
    },
    skonto_amount: function(frm) {
        recalculate_total(frm);
    }
});

frappe.ui.form.on('Payment Proposal Expense', {
    expenses_remove: function(frm) {
        recalculate_total(frm);
    }
});

function recalculate_total(frm) {
    var total = 0;
    for (var i = 0; i < frm.doc.purchase_invoices.length; i++) {
        total += frm.doc.purchase_invoices[i].skonto_amount
    }
    for (var i = 0; i < frm.doc.expenses.length; i++) {
        total += frm.doc.expenses[i].amount
    }
    cur_frm.set_value('total', total);
}

function transmit_ebics(frm) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.ebics_conncetion.ebics_connection.execute_payment',
        'args': {
            'ebics_connection': locals.ebics_connection,
            'payment_proposal': frm.doc.name
        },
        'callback': function (response) {
            frappe.msgprint( __("Payments transferred using ebics") );
        }
    });
}
