import requests
import frappe
from frappe import _

def get_api_credentials():
    account_uuid = frappe.db.get_single_value("AbaNinja Settings", "account_uuid")
    api_key = frappe.get_single_value("AbaNinja Settings", "api_key")

    return account_uuid, api_key

def get_abaninja_headers(api_key):
    return {
        "Authorization": "Bearer {}".format(api_key),
        "Content-Type": "application/json"
    }

@frappe.whitelist()
def sync_abaninja_customers():
    # get credentials
    account_uuid, api_key = get_api_credentials()

    if not account_uuid or not api_key:
        frappe.log_error("AbaNinja Sync Failed", "Syncing AbaNinja Customers failed: Missing UUID or API Key in settings.")
        return {
            "success": False,
            "message": _("Error in UUID/key configuration. Please check your AbaNinja Settings.")
        }
    
    url = "https://api.abaninja.ch/accounts/{0}/addresses/v2/companies".format(account_uuid)
    headers = get_abaninja_headers(api_key)

    stats = {"success": True, "inserted": 0, "updated": 0, "message": ""}

    # get data from AbaNinja API
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            frappe.log_error("AbaNinja Sync API Failure", "Status: {0}\nResponse: {1}".format(response.status_code, response.text))
            return {
                "success": False,
                "message": _("AbaNinja API responded with status {0}. Check System Error Logs.").format(response.status_code)
            }
        
        response_payload = response.json()
        companies = response_payload.get('data', response_payload) if isinstance(response_payload, dict) else response_payload

        # loop through customers and handle data
        for company_data in companies:
            if not company_data.get("company_name"):
                continue
            
            is_new = save_or_update_customer(company_data)

            if is_new:
                stats["inserted"] += 1
            else:
                stats["updated"] += 1

        frappe.db.commit()
        stats["message"] = _("Customers synchronized successfully.")
        return stats

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("AbaNinja Sync Exception", frappe.get_traceback())
        return {
            "success": False,
            "message": _("An unexpected execution crash occurred: {0}").format(str(e))
        }

def find_existing_customer(abaninja_id, tax_id, company_name):
    # try matching customers in DB, first by abaninja_uuid, then by tax_id and then by customer_name
    if abaninja_id:
        customer = frappe.db.get_value("Customer", {"abaninja_id": abaninja_id}, "name")
        if customer: return customer

    if tax_id:
        customer = frappe.db.get_value("Customer", {"tax_id": tax_id}, "name")
        if customer: return customer

    if company_name:
        customer = frappe.db.get_value("Customer", {"customer_name": company_name}, "name")
        if customer: return customer
    
    return None

def save_or_update_customer(company_data):             
    abaninja_id = company_data.get("uuid", "")
    company_name = company_data.get("company_name")
    tax_id = company_data.get("vat_number")

    customer_id = find_existing_customer(abaninja_id, tax_id, company_name)
    is_new = False
    
    # save or update customer
    if customer_id:
        customer_doc = frappe.get_doc("Customer", customer_id)
    else:
        customer_doc = frappe.new_doc("Customer")
        customer_doc.customer_group = _("All Customer Groups")
        customer_doc.territory = _("All Territories")
        customer_doc.customer_type = "Company"
        customer_doc.name = company_data.get('customer_number', '')
        is_new = True

    # add the necessary values
    customer_doc.customer_name = company_name
    customer_doc.abaninja_id = abaninja_id
    if tax_id:
        customer_doc.tax_id = tax_id
    customer_doc.billing_currency = company_data.get("currency_code", "")
    customer_doc.print_language = company_data.get("language", "")
    customer_doc.customer_details = company_data.get("private_notes", "")
    customer_doc.payment_terms = company_data.get("payment_terms", "")
    customer_doc.disabled = company_data.get("is_archived")

    customer_doc.save(ignore_permissions=True)

    # sync related contacts and addresses
    sync_linked_addresses(customer_doc, company_data)
    sync_linked_contacts(customer_doc, company_data)

    return is_new

def sync_linked_addresses(customer_doc, company_data):
    # TODO: link customer and contacts/addresses
    return

def sync_linked_contacts(customer_doc, company_data):


    # TODO: link customer and contacts/addresses

    return