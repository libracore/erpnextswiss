// check if HLK is active, if so, load HLK extension
try {
    frappe.call({
    "method": "erpnextswiss.erpnextswiss.domains.is_domain_active",
    "args": {
        "domain": "HLK"
    },
    "callback": function(response) {
        if (response.message === 1) {
            // load HLK
            var script = document.createElement('script');
            script.onload = function () {
                cur_frm.refresh();
            };
            script.src = "/assets/erpnextswiss/js/hlk_scripts/sales_invoice.js";
            document.head.appendChild(script);
        }
    }
});

} catch {
    // do nothing
}

// normal scripts
frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        
    }
});
