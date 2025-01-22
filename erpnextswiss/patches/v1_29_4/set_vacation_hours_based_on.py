import frappe
from frappe import _

def execute():
    try:
        frappe.reload_doc("erpnextswiss", "doctype", "worktime_settings")
        settings = frappe.get_doc("Worktime Settings", "Worktime Settings")
        settings.vacation_hours_based_on = 'Timesheet'
        settings.save()
        frappe.db.commit()
    except Exception as err:
        print("Unable to execute Patch set_vacation_hours_based_on")
        print(str(err))
    return