frappe.query_reports["Timesheet Month per Project"] = {
    "filters": [
        {
            "fieldname":"from_date",
            "label": __("From date"),
            "fieldtype": "Date"
        },
        {
            "fieldname":"end_date",
            "label": __("End date"),
            "fieldtype": "Date",
            "default" : frappe.datetime.get_today()
        },
        {
            "fieldname":"employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee"
        }
    ]
}
