// Copyright (c) 2019-2020, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ZUGFeRD Wizard', {
	refresh: function(frm) {
        if (frm.doc.ready_for_import == 1) {
            frm.add_custom_button(__("Create invoice"), function() {
                frappe.show_alert( __("doing it...!") );
                
                
                
                frappe.call({
				method: 'hello',
				doc: frm.doc
				})
            });
        }
	},
    // change trigger on the file
    file: function(frm) {
        if (frm.doc.file) {
            // has a file --> read & interpret
            frappe.call({
                method: 'read_file',
                doc: frm.doc,
                callback: function(response) {
                   var content = response.message;
                   cur_frm.set_df_property('preview_html', 'options', content.html);
                   cur_frm.set_value('content_dict', content.dict);
                   cur_frm.set_value('ready_for_import', 1);
                }
            });
            
        } else {
            // no file --> clear
            cur_frm.set_df_property('preview_html', 'options', __("Please load a file...") );
            cur_frm.set_value('ready_for_import', 0);
        }
        
    }
    
    
    
    
    
});
