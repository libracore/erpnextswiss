var uploaded_files = [];

frappe.pages['bkp-importer'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'BKP Importer',
		single_column: true
	});
	
	frappe.bkpimporter.make(page);
	frappe.bkpimporter.run();
	
	// add the application reference
	frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.bkpimporter = {
	start: 0,
	make: function(page) {
		var me = frappe.bkpimporter;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('bkp_importer', data)).appendTo(me.body);
		
		// add menu button
		this.page.add_menu_item(__("Upload Files"), function() {
			frappe.bkpimporter.new_attachment();
		});
		// add menu button
		this.page.add_menu_item(__("Import / Update BKP Items from uploaded Files"), function() {
			frappe.bkpimporter.starting_import(uploaded_files);
		});
	},
	run: function() {
	},
	new_attachment: function() {
		var me = this;
		if (this.dialog) {
			this.dialog.$wrapper.remove();
		}
		new frappe.ui.FileUploader({
			folder: 'Home/BKP-Uploads',
			upload_notes: 'Sie können/dürfen nur "BKP" .xml Files hochladen. .xml Files > 40MB als .zip File!',
			restrictions: {
				allowed_file_types: ['.xml', '.zip']
			},
			allow_multiple: false,
			on_success: (file_doc) => {
				if (document.getElementById('data_place_holder')) {
					document.getElementById('data_place_holder').outerHTML = "";
				}
				$("#extracted_data").removeClass("hidden");
				console.log("upload ok, starte parsing");
				document.getElementById('overlay').innerHTML = "Upload done, start parsing...";
				openNav();
				frappe.bkpimporter.read_master_content_of_bkp_xml(file_doc);
			}
		});
	},
	read_master_content_of_bkp_xml: function(file_doc) {
		if (file_doc) {
			frappe.call({
				method: 'erpnextswiss.erpnextswiss.page.bkp_importer.bkp_importer.read_xml',
				args: {
					'file_path': file_doc.file_url,
					'name': file_doc.file_name
				},
				callback: function(r) {
					if (r.message != 'Error') {
						console.log("daten geparst:");
						console.log(r.message);
						uploaded_files.push(r.message.name);
						show_preview_data(r.message);
					} else {
						console.log("fehler beim parsen");
					}
				}
			});
		}
		else
		{
			frappe.msgprint(__("Please select a file."), __("Information"));
		}
	},
	starting_import: function(files) {
		console.log("files:");
		console.log(files);
		if (files) {
			frappe.call({
				method: 'erpnextswiss.erpnextswiss.page.bkp_importer.bkp_importer.import_update_items',
				args: {
					'xml_files': files
				}
			});
			if (document.getElementById('extracted_data')) {
				document.getElementById('extracted_data').outerHTML = "";
			}
			$("#bitte_warten").removeClass("hidden");
		}
	}
}

function show_preview_data(data) {
	var output = [];
	output.push('<tr>');
	output.push('<td>' + data.name + '</td>');
	output.push('<td>' + data.katalog_daten.Txt_Katalog + ' (' + data.katalog_daten.ID_Katalog +')</td>');
	output.push('<td>' + data.katalog_daten.Versions_Jahr + ' - ' + data.katalog_daten.Versions_Nr + '</td>');
	output.push('<td>' + data.katalog_daten.Preisbuch_Nr + '</td>');
	output.push('<td>' + data.katalog_daten.Dat_Valid_Von + '</td>');
	output.push('<td>' + data.katalog_daten.Sprache + '</td>');
	output.push('</tr>');
	document.getElementById('table_body').innerHTML = document.getElementById('table_body').innerHTML + output.join('');
	
	closeNav();
}

function openNav() {
  document.getElementById("myNav").style.width = "100%";
}

function closeNav() {
  document.getElementById("myNav").style.width = "0%";
} 