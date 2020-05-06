frappe.pages['zugferd_assistant'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Zugferd Assistant',
		single_column: true
	});
	frappe.zugferd_assistant.make(page);

    // add the application reference
    frappe.breadcrumbs.add("ERPNextSwiss");
	
}


frappe.zugferd_assistant = {
    start: 0,
    make: function(page) {
        var me = frappe.zugferd_assistant;
        me.page = page;
        me.body = $('<div></div>').appendTo(me.page.main);
        var data = "";
        $(frappe.render_template('zugferd_assistant', data)).appendTo(me.body);
        
        // file handler for import button
        this.page.main.find(".btn-import-file").on('click', function(event, debug=false) {
            //frappe.zugferd_assistant.read_file();
            var options = {
                allow_multiple: false,
                on_success: file => {
                    frappe.zugferd_assistant.upload_complete(file)
                }
            }
            this.file_uploader = new frappe.ui.FileUploader(options);
            
        });
    },
   
    read_file: function(file) {
        if (document.getElementById("input_file").files.length > 0) {
            var file = document.getElementById("input_file").files[0];
			console.log("importes file is type of: " + typeof(file))
			console.log("found file " + file.name);
			
            if (file.name.toLowerCase().endsWith(".pdf")) {
                console.log("create reader instance...");
                // create a new reader instance
                var reader = new FileReader();
                // assign load event to process the file
                reader.onload = function (event) {
                    console.log("file read...");
                    // read file content
                    var content = event.target.result
                    // convert from ArrayBuffer to bytes
                    //var bytes = new Uint8Array(content);
                    // call parser
                    frappe.zugferd_assistant.parse(content);
                }
                // assign an error handler event
                reader.onerror = function (event) {
                    frappe.msgprint(__("Error reading file"), __("Error"));
                }
                console.log("read binary...");
                //reader.readAsArrayBuffer(file);
                reader.readAsBinaryString(file);
            } 
        } else {
            frappe.msgprint( __("Please select a file to import") );
        }
    },
    parse: function(content){
        console.log(content);
        frappe.call({
            method: 'erpnextswiss.erpnextswiss.zugferd.zugferd.import_pdf',
            args: {
                'content': content 
            },
            callback: function(r) {
                frappe.msgprint("done");
                console.log(r.message);
            }
        });
        
        
    },
    upload_complete: function(file) {
        console.log(file);
    }
}
