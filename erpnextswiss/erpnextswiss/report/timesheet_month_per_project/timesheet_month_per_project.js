frappe.query_reports["Timesheet Month per Project"] = {
    "filters": [
        {
            "fieldname":"from_time",
            "label": __("From time"),
            "fieldtype": "Datetime"
        },
        {
            "fieldname":"end_date",
            "label": __("End date"),
            "fieldtype": "Date"
        }
    ]
}
