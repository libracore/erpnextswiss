frappe.listview_settings['Contract'] = {
    add_fields: ["status", "has_pending_final_period", "unbilled_days_remaining"],
    
    get_indicator: function(doc) {
        if (doc.status === "Inactive" && doc.has_pending_final_period) {
            return [
                __("Pending Final Invoice ({0} Days)", [doc.unbilled_days_remaining]), 
                "orange", 
                "has_pending_final_period,=,1"
            ];
        }

        if (doc.status === "Active") {
            return [__("Active"), "green", "enabled,=,1"];
        } else {
            return [__("Disabled"), "gray", "enabled,=,0"];
        }
    }
};