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
    #sync_linked_contacts(customer_doc, company_data)

    return is_new

def sync_linked_addresses(customer_doc, company_data):
    addresses = company_data.get("addresses", [])
    
    for addr in addresses:
        abaninja_id = addr.get("uuid")
        street = addr.get("address", "")
        street_num = addr.get("street_number", "")
        extension = addr.get("extension", "")
        additional_field = addr.get("additional_field", "")
        city = addr.get("city")
        zip_code = addr.get("zip_code")
        country_iso = addr.get("country_code", "CH")

        if not street and not city:
            continue

        # format address lines
        full_street = street + " " +street_num
        parts = [p for p in [extension, additional_field] if p]
        additional_info = " ".join(parts)
        address_title = customer_doc.customer_name + "-" + "Billing"
        
        address_name = frappe.db.get_value("Address", {"abaninja_id": abaninja_id}, "name")
        if address_name:
            address = frappe.get_doc("Address", address_name)
        else:
            address = frappe.new_doc("Address")
            address.address_title = address_title
            address.address_type = "Billing"

        address.abaninja_id = abaninja_id
        address.address_line1 = full_street
        address.address_line2 = additional_info
        address.city = city
        address.pincode = zip_code
        
        # get country from iso_code
        # TODO: handle country (there are a lot)
        address.country = "Switzerland" if country_iso == "CH" else ("Germany" if country_iso == "DE" else country_iso)
        address.save(ignore_permissions=True)

        # map address to company
        if not frappe.db.exists("Dynamic Link", {"parent": address.name, "link_doctype": "Customer", "link_name": customer_doc.name}):
            address.append("links", {
                "link_doctype": "Customer",
                "link_name": customer_doc.name
            })
            address.save(ignore_permissions=True)
    return

def sync_linked_contacts(customer_doc, company_data):
    company_email = None
    company_phone = None

    for contact_value in company_data.get("contacts", []):
        if contact_value.get("type") == "email":
            company_email = contact_value.get("value")
        elif contact_value.get("type") == "phone":
            company_phone = contact_value.get("value")
    
    # create a default contact for the company


    persons = company_data.get("contact_persons", [])

    for person in persons:
        first_name = person.get("first_name", "")
        last_name = person.get("last_name", "")
        
        person_email = None
        person_phone = None
        for c in person.get("contacts", []):
            if c.get("type") == "email":
                person_email = c.get("value")
            elif c.get("type") == "phone":
                person_phone = c.get("value")
                
        # Fallback to general company phone if person lacks a direct phone extension
        if not person_phone:
            person_phone = company_phone

        create_or_update_contact(
            customer_doc=customer_doc,
            first_name=first_name,
            last_name=last_name,
            email=person_email or company_email,
            phone=person_phone
        )

    return 

def create_or_update_contact(customer_doc, first_name, last_name, email, phone):
    contact_name = None
    if email:
        contact_name = frappe.db.get_value("Contact", {"email_id": email}, "name")
    elif phone:
        contact_name = frappe.db.get_value("Contact", {"phone": phone}, "name")

    if contact_name:
        contact = frappe.get_doc("Contact", contact_name)
    else:
        contact = frappe.new_doc("Contact")
        contact.first_name = first_name or customer_doc.customer_name
        contact.last_name = last_name

    if email: contact.email_id = email
    if phone: contact.phone = phone
    contact.save(ignore_permissions=True)
    
    # Create reference map link to Customer record
    if not frappe.db.exists("Dynamic Link", {"parent": contact.name, "link_doctype": "Customer", "link_name": customer_doc.name}):
        contact.append("links", {
            "link_doctype": "Customer",
            "link_name": customer_doc.name
        })
        contact.save(ignore_permissions=True)
    return