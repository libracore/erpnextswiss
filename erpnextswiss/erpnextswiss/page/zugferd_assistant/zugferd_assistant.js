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
        
        this.page.main.find(".btn-import-file").on('click', function(event, debug=false) {
			
		
			
			
			console.log("success")
			 var file = document.getElementById("input_file").files[0];
			console.log("importes file is type of: " + typeof(file))
			console.log("found file " + file.name);
			
    if (file.name.toLowerCase().endsWith(".pdf")) {
        console.log("create reader instance...");
        // create a new reader instance
        var reader = new FileReader();
        // assign load event to process the file
        reader.onload = function (event) {
			// read file content
			//content = String.fromCharCode.apply(null, Array.prototype.slice.apply(new Uint8Array(event.target.result)));
            //var content = btoa(String.fromCharCode.apply(null, new Uint8Array(event.target.result)));
            var uint8ar = new Uint8Array(event.target.result)
            var st = new TextDecoder().decode(uint8ar)
           
             
            //console.log("content name..." + uint8ar.name);
            //console.log("content is..." + typeof(uint8ar));
             
            console.log("st is..." + st);
            console.log("st type of is..." + typeof(st));
            // read file content
            //console.log("reading file...");
            var t = event.target.result
            //console.log("reader result" + reader.result);
           
            //console.log( "event t " + t)
            //console.log("type of t " + typeof(t))
            
            //console.log("only reader" + reader);
            //console.log("reader ersult is" + reader.result);
           
            // call pars
            frappe.zugferd_assistant.send_read(st);
        }
        // assign an error handler event
        reader.onerror = function (event) {
            frappe.msgprint(__("Error reading file"), __("Error"));
        }
        console.log("read binary...");
        reader.readAsArrayBuffer(file);
    } //if file end with
			
			}); //this. button handler
			
			
    },
    

send_read: function(inp){
    
    frappe.call({
                method: 'erpnextswiss.erpnextswiss.zugferd.zugferd.import_pdf',
                args: {
                    'pdf_file1': inp 
                },          
                callback: function(r) {
                    if (r.message) {                  
                    } 
                }
            });
	}
} //func
