frappe.pages['abacus_export'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Abacus Export'),
        single_column: true
    });

    frappe.abacus_export.make(page);
    frappe.abacus_export.run();
    frappe.abacus_export.update_preview();
    
    // add the application reference
    frappe.breadcrumbs.add("ERPNextSwiss");
}


frappe.abacus_export = {
    start: 0,
    make: function(page) {
        var me = frappe.abacus_export;
        me.page = page;
        me.body = $('<div></div>').appendTo(me.page.main);
        var data = "";
        $(frappe.render_template('abacus_export', data)).appendTo(me.body);
        
        // attach button handlers
        this.page.main.find(".btn-create-file").on('click', function() {
            frappe.abacus_export.create_transfer_file();
        });
        
        // add menu button
        this.page.add_menu_item(__("Reset export flags"), function() {
            frappe.abacus_export.reset_export_flags();
        });
    },
    run: function() {
        // set beginning of the year as start and today as current date
        var today = new Date();
        var dd = today.getDate();
        if (dd < 10) { dd = "0" + dd; }
        var mm = today.getMonth() + 1;     //January is 0!
        if (mm < 10) { mm = "0" + mm; }
        var yyyy = today.getFullYear();
        var input_start = document.getElementById("start_date");
        input_start.value = yyyy + "-01-01";
        var input_end = document.getElementById("end_date");
        input_end.value = yyyy + "-" + mm + "-" + dd;
        
        // attach change handlers
        input_start.onchange = function() { frappe.abacus_export.update_preview(); };
        input_end.onchange = function() { frappe.abacus_export.update_preview(); };
    },
    update_preview: function() {
        // get date values
        start_date = document.getElementById("start_date").value;
        end_date = document.getElementById("end_date").value;
        if ((start_date == null) || (start_date == "")) {
            start_date = "2000-01-01";
        }
        if ((end_date == null) || (end_date == "")) {
            end_date = "2999-01-01";
        }
        if (end_date < start_date) {
            // switch values
            document.getElementById("start_date").value = end_date;
            document.getElementById("end_date").value = start_date;
            var temp = start_date;
            start_date = end_date;
            end_date = temp;
        }
        // get GL entries from this period
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype:"GL Entry",
                filters: [
                    ["posting_date",">=", start_date],
                    ["posting_date","<=", end_date],
                    ["docstatus","=", 1],
		    ["exported_to_abacus","=",0]
                ],
                fields: ["posting_date", "debit", "credit", "account", "voucher_type", "voucher_no"],
                order_by: "posting_date"
            },
            callback: function(response) {
                var preview_container = document.getElementById("preview");
                preview_container.innerHTML = "";
                if (response.message) {
                    if (response.message.length > 0) {
                        preview_container.innerHTML += frappe.render_template('gl_entry_table', response);
                    } 
                    if (response.message.length == 20) {
                        preview_container.innerHTML += '<p class="text-muted">' + __("more records available (not shown)") + '</p>';
                    }
                } else {
                    preview_container.innerHTML += '<p class="text-muted">' + __("No general ledger entries found.") + '</p>';
                }
            }
        });
    },
    create_transfer_file: function() {
        // enable waiting gif
        document.getElementById("waiting-gif").classList.remove("hide");
        // get date range
        var start_date = document.getElementById("start_date").value;
        var end_date = document.getElementById("end_date").value;
        var aggregated = 0;
        if (document.getElementById("chk-aggregated").checked) {
            aggregated = 1;
        }
        // generate payment file
        frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.abacus_export.abacus_export.generate_transfer_file',
            args: { 
                'start_date': start_date,
                'end_date': end_date,
                'aggregated': aggregated
            },
            callback: function(r) {
                if (r.message) {
                    // prepare the xml file for download
                    frappe.abacus_export.download("transfer.xml", r.message.content);
                    
                    // disable waiting gif
                    document.getElementById("waiting-gif").classList.add("hide");
		    
                    // update content
                    frappe.abacus_export.update_preview();
                } 
            }
        });
    },
    download: function (filename, content) {
        var element = document.createElement('a');
        element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    },
    reset_export_flags: function () {
        frappe.call({
            method: 'erpnextswiss.erpnextswiss.page.abacus_export.abacus_export.reset_export_flags',
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert( __("Export flags reset") );
		    frappe.abacus_export.update_preview();
                } 
            }
        });
    }
}

