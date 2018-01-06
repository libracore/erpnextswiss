frappe.pages['payment_export'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Payment Export'),
		single_column: true
	});

	frappe.payment_export.make(page);
	frappe.payment_export.run(page);
}

frappe.payment_export = {
	start: 0,
	make: function(page) {
		var me = frappe.payment_export;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('payment_export', data)).appendTo(me.body);

		// attach button handlers
		this.page.main.find(".btn-create-file").on('click', function() {
			var me = frappe.payment_export;
			
            // find selected payments
            var checkedPayments = findSelected();
            if (checkedPayments.length > 0) {
                var payments = [];
                for (var i = 0; i < checkedPayments.length; i++) {
                    payments.push(checkedPayments[i].name);
                }
                
                // generate payment file
                frappe.call({
                    method: 'erpnextswiss.erpnextswiss.page.payment_export.payment_export.generate_payment_file',
                    args: { 
                        'payments': payments
                    },
                    callback: function(r) {
                        if (r.message) {
                            // prepare the xml file for download
                            download("payments.xml", r.message.content);
                        } 
                    }
                });
                
            } else {
                frappe.msgprint( __("Please select at least one payment."), __("Information") );
            }
            
            // 

		});
	},
	run: function(page) {  
		// populate payment entries
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.payment_export.payment_export.get_payments',
			args: { },
			callback: function(r) {
				if (r.message) {
					var parent = page.main.find(".payment-table").empty();
                    if (r.message.payments.length > 0) {
                        $(frappe.render_template('payment_export_table', r.message)).appendTo(parent);
                    } else {
                        $('<h3>No payment entries to be paid found with status draft</h3>').appendTo(parent);
                    }
				} 
			}
		});
	}
}

function download(filename, content) {
  var element = document.createElement('a');
  element.setAttribute('href', 'application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}

function findSelected() {
    var inputs = document.getElementsByTagName("input"); 
    var checkboxes = []; 
    var checked = []; 
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].type == "checkbox") {
        checkboxes.push(inputs[i]);
        if (inputs[i].checked) {
          checked.push(inputs[i]);
        }
      }
    }
    return checked;
}
