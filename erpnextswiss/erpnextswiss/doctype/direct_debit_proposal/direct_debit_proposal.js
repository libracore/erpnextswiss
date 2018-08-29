// Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Direct Debit Proposal', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1) {
			// add download pain.008 button on submitted record
			frm.add_custom_button(__("Download bank file"), function() {
				generate_bank_file(frm);
			});
		}
	}
});

function generate_bank_file(frm) {
	frappe.call({
		method: 'create_bank_file',
		args: { 
			'doc': frm.doc
		},
		callback: function(r) {
			if (r.message) {
				// prepare the xml file for download
				download("lsv.xml", r.message.content);
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
