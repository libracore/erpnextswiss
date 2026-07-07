import requests
import frappe
from frappe import _

def get_api_credentials():
    account_uuid = frappe.db.get_single_value("AbaNinja Settings", "account_uuid")
    abaninja_settings = frappe.get_single("AbaNinja Settings")
    api_key = abaninja_settings.get_password('api_key')  

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

def get_or_create_payment_terms_template(days):
    template_name = str(days).strip()
    
    if template_name == "-1":
        term_days = 0
        term_name = "0 Days"
    else:
        try:
            term_days = int(template_name)
            term_name = "{term_days} Days".format(term_days=term_days)
        except ValueError:
            frappe.log_error("AbaNinja Terms Error", "Invalid days value received: {days_raw}".format(days_raw=days_raw))
            return None

    if not frappe.db.exists("Payment Term", term_name):
        try:
            term_doc = frappe.new_doc("Payment Term")
            term_doc.payment_term_name = term_name
            term_doc.credit_days = term_days
            term_doc.invoice_portion = 100.0
            term_doc.due_date_based_on = "Day(s) after invoice date"
            term_doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error("Failed to Create Payment Term", frappe.get_traceback())
            return None

    if frappe.db.exists("Payment Terms Template", template_name):
        return template_name

    try:
        template_doc = frappe.new_doc("Payment Terms Template")
        template_doc.template_name = template_name
        
        template_doc.append("terms", {
            "payment_term": term_name,
            "invoice_portion": 100.0,
            "credit_days": term_days
        })
        
        template_doc.insert(ignore_permissions=True)
        return template_doc.name

    except Exception as e:
        frappe.log_error("Failed to Create Payment Terms Template", "Could not build template '{template_name}'. Error:".format(template_name=template_name) + " " + {frappe.get_traceback()})
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
        if company_data.get('customer_number'):
            customer_doc.name = company_data.get('customer_number')
        is_new = True

    # find/generate payment terms
    payment_terms = None
    if company_data.get("payment_terms"):
        payment_terms = get_or_create_payment_terms_template(company_data.get("payment_terms"))

    # add the necessary values
    customer_doc.customer_name = company_name
    customer_doc.abaninja_id = abaninja_id
    customer_doc.tax_id = tax_id or ""
    customer_doc.default_currency = company_data.get("currency_code", "")
    customer_doc.language = company_data.get("language", "")
    customer_doc.customer_details = company_data.get("private_notes", "")
    customer_doc.payment_terms = payment_terms
    customer_doc.disabled = 1 if company_data.get("is_archived") else 0

    customer_doc.save(ignore_permissions=True)

    # sync related contacts and addresses
    sync_linked_addresses(customer_doc, company_data)
    sync_linked_contacts(customer_doc, company_data)

    return is_new

def sync_linked_addresses(customer_doc, company_data):
    addresses = company_data.get("addresses", [])
    if not addresses:
        return

    # get default contact info
    email_list = []
    phone_list = []

    for contact_value in company_data.get("contacts", []):
        contact_type = contact_value.get("type")
        contact_val = contact_value.get("value")

        if not contact_val:
            continue

        if contact_type == "email":
            email_list.append(contact_val.strip())
        elif contact_type == "phone":
            phone_list.append(contact_val.strip())

    email_id = ", ".join(email_list)
    phone = ", ".join(phone_list)
    is_disabled = 1 if company_data.get("is_archived") else 0

    for addr in addresses:
        abaninja_id = addr.get("uuid")
        street = addr.get("address") or "-"
        street_num = addr.get("street_number", "")
        extension = addr.get("extension", "")
        additional_field = addr.get("additional_field", "")
        city = addr.get("city")
        zip_code = addr.get("zip_code")
        country_iso = addr.get("country_code", "CH").lower()

        if not street and not city:
            continue

        # format address lines
        street_parts = [p for p in [street, street_num] if p]
        full_street = " ".join(street_parts)
        parts = [p for p in [extension, additional_field] if p]
        additional_info = " ".join(parts)
        address_title = customer_doc.customer_name
        
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
        address.disabled = is_disabled
        address.email_id = email_id
        address.phone = phone
        
        # get country from iso_code
        country = frappe.db.get_value("Country", {"code": country_iso}, "name")
        if country:
            address.country = country
        else:
            address.country = "Switzerland"

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
    persons = company_data.get("contact_persons", [])

    for person in persons:
        abaninja_id = person.get("uuid")
        first_name = person.get("first_name", "")
        last_name = person.get("last_name", "")
        salutation = person.get("salutation", "")
        
        person_email = None
        person_phone = None
        for c in person.get("contacts", []):
            if c.get("type") == "email":
                person_email = c.get("value")
                person_email_primary = c.get("is_primary")
            elif c.get("type") == "phone":
                person_phone = c.get("value")
                person_phone_primary = c.get("is_primary")
        
        contact_name = frappe.db.get_value("Contact", {"abaninja_id": abaninja_id}, "name")

        if contact_name:
            contact = frappe.get_doc("Contact", contact_name)
        else:
            contact = frappe.new_doc("Contact")
            contact.abaninja_id = abaninja_id
            contact.first_name = first_name
            contact.last_name = last_name
        
        contact.salutation = salutation
        
        # add email to email_id table
        if person_email:
            email_exists = False
            for row in contact.get("email_ids"):
                if row.email_id == person_email:
                    row.is_primary = person_email_primary
                    email_exists = True
                    break

            if not email_exists:
                contact.append("email_ids", {"email_id": person_email, "is_primary": person_email_primary})

        # add phone to phone_no table
        if person_phone:
            phone_exists = False
            for row in contact.get("phone_nos"):
                if row.phone == person_phone:
                    row.is_primary_phone = person_phone_primary
                    phone_exists = True
                    break

            if not phone_exists:
                contact.append("phone_nos", {"phone": person_phone, "is_primary_phone": person_phone_primary})


        contact.save(ignore_permissions=True)
    
        # map contact to company
        if not frappe.db.exists("Dynamic Link", {"parent": contact.name, "link_doctype": "Customer", "link_name": customer_doc.name}):
            contact.append("links", {"link_doctype": "Customer", "link_name": customer_doc.name})
            contact.save(ignore_permissions=True)

    return 

@frappe.whitelist()
def sync_abaninja_items():
    # get credentials
    account_uuid, api_key = get_api_credentials()

    if not account_uuid or not api_key:
        frappe.log_error("AbaNinja Sync Failed", "Syncing AbaNinja Customers failed: Missing UUID or API Key in settings.")
        return {
            "success": False,
            "message": _("Error in UUID/key configuration. Please check your AbaNinja Settings.")
        }
    
    url = "https://api.abaninja.ch/accounts/{0}/products/v2/products".format(account_uuid)
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
        items = response_payload.get('data', response_payload) if isinstance(response_payload, dict) else response_payload

        # loop through items and handle data
        for item in items:
            product_name = (
                item.get("translations", {}).get("de", {}).get("productName") or 
                item.get("translations", {}).get("en", {}).get("productName") or 
                item.get("productKey")
            )
            if not product_name:
                continue

            is_new = save_or_update_item(item)

            if is_new:
                stats["inserted"] += 1
            else:
                stats["updated"] += 1

        frappe.db.commit()
        stats["message"] = _("Items synchronized successfully.")
        return stats

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("AbaNinja Sync Exception", frappe.get_traceback())
        return {
            "success": False,
            "message": _("An unexpected execution crash occurred: {0}").format(str(e))
        }

def save_or_update_item(item):
    abaninja_id = item.get("productUuid") or item.get("uuid")
    product_key = item.get("productKey")

    # get german product name and description
    translations = item.get("translations", {})
    de_trans = translations.get("de", {})

    item_name = de_trans.get("productName") or product_key
    description = de_trans.get("productDescription") or ""

    if product_key:
        item_code = frappe.db.get_value("Item", {"item_code": product_key}, "name")

    is_new = False
    
    if item_code:
        item_doc = frappe.get_doc("Item", item_code)
    else:
        item_doc = frappe.new_doc("Item")
        item_doc.item_code = product_key
        is_new = True

    # handle UOM
    uom = "Nos" # default
    unit_data = item.get("productUnit")
    if unit_data:
        uom = get_or_create_uom(unit_data)

    # handle item group
    item_group_name = "All Item Groups" # default
    group_data = item.get("productGroup")
    if group_data:
        item_group_name = get_or_create_item_group(group_data)

    item_doc.item_name = item_name[:140] # truncate item_name, as ERPNext only allows up to 140 characters
    item_doc.abaninja_id = abaninja_id
    item_doc.item_group = item_group_name
    item_doc.stock_uom = uom
    item_doc.description = description
    
    # service item -> remove 'is_stock_item'
    if item.get("isService"):
        item_doc.is_stock_item = 0
    else:
        item_doc.is_stock_item = 1

    item_doc.disabled = 1 if item.get("archivedAt") else 0
    
    if item.get("eanCode"):
        item_doc.set("barcodes", [])
        item_doc.append("barcodes", {
            "barcode": item.get("eanCode"),
            "barcode_type": "EAN"
        })

    item_doc.save(ignore_permissions=True)

    if item.get("cost"):
        update_item_price_or_cost(item_doc.name, item.get("cost"))

    return is_new

def get_or_create_uom(unit_data):
    uom_id = unit_data.get("translations", {}).get("de", {}).get("unit")
    
    if not uom_id:
        return "Nos"
        
    if not frappe.db.exists("UOM", uom_id):
        try:
            uom_doc = frappe.new_doc("UOM")
            uom_doc.uom_name = uom_id
            uom_doc.must_be_whole_number = 0
            uom_doc.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
            
    return uom_id

def get_or_create_item_group(group_data):
    group_name = group_data if isinstance(group_data, str) else group_data.get("productGroupDescription")
    
    if not group_name:
        return "All Item Groups"

    if not frappe.db.exists("Item Group", group_name):
        try:
            ig_doc = frappe.new_doc("Item Group")
            ig_doc.item_group_name = group_name
            ig_doc.parent_item_group = "All Item Groups"
            ig_doc.is_group = 0
            ig_doc.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
            
    return group_name

def update_item_price_or_cost(item_code, cost_price):
    try:
        abaninja_settings = frappe.get_single("AbaNinja Settings")
        price_list = abaninja_settings.get("item_price_list")

        if not price_list or not frappe.db.exists("Price List", price_list):
            raise frappe.ValidationError(
                _("AbaNinja Sync Failed: Missing or invalid Price List in AbaNinja Settings.")
            )
        
        existing_price = frappe.db.get_value(
            "Item Price", 
            {"item_code": item_code, "price_list": price_list}, 
            "name"
        )
        
        if existing_price:
            frappe.db.set_value("Item Price", existing_price, "price_list_rate", cost_price)
        else:
            ip = frappe.new_doc("Item Price")
            ip.item_code = item_code
            ip.price_list = price_list
            ip.price_list_rate = cost_price
            ip.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            "AbaNinja Price Sync Exception", 
            "Failed to update price for item {0}: {1}\n{2}".format(item_code, str(e), frappe.get_traceback())
        )
        raise e


