import frappe
from frappe import _

def execute():
    # this will create some standard datatrans payment methods
    try:
        frappe.reload_doc("erpnextswiss", "doctype", "datatrans_settings")
        frappe.reload_doc("erpnextswiss", "doctype", "datatrans_payment_method")
        settings = frappe.get_doc("Datatrans Settings", "Datatrans Settings")
        if len(settings.payment_methods) == 0:
            settings.append("payment_methods", {"method": "Mastercard", "code": "ECA"})
            settings.append("payment_methods", {"method": "Visa", "code": "VIS"})
            settings.append("payment_methods", {"method": "Cryptocurrencies (Coinify)", "code": "CFY"})
            settings.append("payment_methods", {"method": "Google Pay", "code": "PAY"})
            settings.append("payment_methods", {"method": "Apple Pay", "code": "APL"})
            settings.append("payment_methods", {"method": "Amazon Pay", "code": "AZP"})
            settings.append("payment_methods", {"method": "Maestro", "code": "MAU"})
            settings.append("payment_methods", {"method": "PayPal", "code": "PAP"})
            settings.append("payment_methods", {"method": "PostFinance Card", "code": "PFC"})
            settings.append("payment_methods", {"method": "PostFinance E-Finance", "code": "PEF"})
            settings.append("payment_methods", {"method": "Reka", "code": "REK"})
            settings.append("payment_methods", {"method": "Samsung Pay", "code": "SAM"})
            settings.append("payment_methods", {"method": "Sofort", "code": "DIB"})
            settings.append("payment_methods", {"method": "TWINT", "code": "TWI"})
            settings.flags.ignore_mandatory = True
            settings.save()
            frappe.db.commit()
    except Exception as err:
        print("Unable to create datatrans payment methods")
    return

    
