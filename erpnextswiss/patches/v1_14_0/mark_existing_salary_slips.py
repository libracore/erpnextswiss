import frappe
from frappe import _

def execute():
    # this will mark all existing salary slips as proposed and prevent, that they will go into a payment run
    frappe.db.sql("""UPDATE `tabSalary Slip` SET `is_proposed` = 1;""")
    return
    
    
