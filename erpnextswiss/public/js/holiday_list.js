frappe.ui.form.on('Holiday List', {
    refresh(frm) {
        // add function to pull data from the internet
        frm.add_custom_button(__("Import"), function() {
            import_holidays(frm);
        });
    }
});

function import_holidays(frm) {
    frappe.prompt([
            {'fieldname': 'region', 'fieldtype': 'Select', 'label': __('Region'), 'reqd': 1, 'options': 'AG\nAR\nAI\nBL\nBS\nBE\nFR\nGE\nGL\nGR\nJU\nLU\nNE\nNW\nOW\nSH\nSZ\nSO\nSG\nTI\nTG\nUR\nVD\nVS\nZG\nZH'},
            {'fieldname': 'year', 'fieldtype': 'Data', 'label': __('Year'), 'readonly': 1, 'default': (frm.doc.to_date || (new Date()).toISOString()).substring(0,4)}
        ],
        function(values){
            frappe.call({
                'method': 'erpnextswiss.erpnextswiss.calendar.parse_holidays',
                'args': {
                    'region': values.region,
                    'year': values.year
                },
                'callback': function(response) {
                    var holidays = response.message;
                    for (var i = 0; i < holidays.length; i++) {
                        var child = cur_frm.add_child('holidays');
                        var date_unc = (new Date(
                            holidays[i].date.substring(6, 10), 
                            parseInt(holidays[i].date.substring(3, 5)) - 1,  // js has 0-based months!!
                            holidays[i].date.substring(0, 2),
                            12                                              // use mid-day before UNC conversion
                        )).toISOString().substring(0, 10);
                        frappe.model.set_value(child.doctype, child.name, 'holiday_date', date_unc);
                        frappe.model.set_value(child.doctype, child.name, 'description', holidays[i].description);
                    }
                    cur_frm.refresh_field('holidays');
                }
            });
        },
        __('Select region'),
        __('Import')
    );
}
