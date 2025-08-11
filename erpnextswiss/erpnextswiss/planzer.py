# Copyright (c) 2024, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.password import get_decrypted_password
import os
import codecs
from datetime import datetime, timedelta
import pysftp

@frappe.whitelist()
def create_shipment(shipment_name, debug=False):
    if not frappe.db.exists("Shipment", shipment_name):
        frappe.throw( _("Shipment {0} not found.").format(shipment_name) )
        
    # prepare data structure
    settings = frappe.get_doc("Planzer Settings", "Planzer Settings")
    if not cint(settings.enabled):
        return
        
    shipment = frappe.get_doc("Shipment", shipment_name)
    sender_address = frappe.get_doc("Address", shipment.pickup_address_name)
    receiver_address = frappe.get_doc("Address", shipment.delivery_address_name)
    delivery_note = frappe.get_doc("Delivery Note", shipment.shipment_delivery_note[0].delivery_note)
    data = {
        'sender': {
            'sender_type': "G",
            'salutation': None,
            'first_name': None,
            'last_name': None,
            'company': shipment.pickup_company,
            'company_addition': None,
            'country': (frappe.get_value("Country", sender_address.country, "code") or "ch").upper(),
            'city': sender_address.city,
            'plz': sender_address.pincode,
            'street': sender_address.address_line1,
            'street_no': sender_address.get('street_no'),
            'gps_lat': sender_address.get('gps_lat'),
            'gps_long': sender_address.get('gps_long'),
            'instructions': shipment.get("instructions"),
            'phone': None,
            'mobile': None,
            'notification': None,
            'email': None,
            'email_notification': None,
            'language': "de"
        },
        'receiver': {
            'company_addition': None,
            'country': (frappe.get_value("Country", receiver_address.country, "code") or "ch").upper(),
            'city': receiver_address.city,
            'plz': receiver_address.pincode,
            'street': receiver_address.address_line1,
            'street_no': receiver_address.get('street_no'),
            'gps_lat': receiver_address.get('gps_lat'),
            'gps_long': receiver_address.get('gps_long'),
            'instructions': shipment.get("instructions"),
            'phone': None,
            'mobile': None,
            'notification': None,
            'email': None,
            'email_notification': None,
        },
        'parcels': [],
        'pickup_date': shipment.pickup_date.strftime("%d.%m.%Y"),
        'pickup_from_time': ("{0}".format(shipment.pickup_from))[0:8],
        'pickup_to_time': ("{0}".format(shipment.pickup_to))[0:8],
        'account_id': settings.account_id,
        'customer_no': settings.customer_no,
        'department_no': settings.department_no,
        'options': [],
        'reference': delivery_note.po_no or delivery_note.name
    }
    sender_contact = None
    if shipment.pickup_contact_name:            # note: the pickup_contact_person is a User
        sender_contact = frappe.get_doc("Contact", shipment.pickup_contact_name)
    elif shipment.pickup_contact_person:        # this is a fallback because pickup_contact_name is unreliable
        sender_contacts = frappe.get_list("Contact", filters={'user': shipment.pickup_contact_person}, fields=['name'])
        if len(sender_contacts) > 0:
            sender_contact = frappe.get_doc("Contact", sender_contacts[0]['name'])
    if sender_contact:
        data['sender'].update({
            'contact_salutation': sender_contact.salutation,
            'contact_first_name': sender_contact.first_name,
            'contact_last_name': sender_contact.last_name,
            'contact_instruction': shipment.get('instruction'),
            'contact_phone': sender_contact.phone,
            'contact_mobile': sender_contact.mobile_no,
            'contact_notification': None,
            'contact_email': sender_contact.email_id,
            'contact_email_notification': None,
            'contact_language': sender_contact.get("language"),
        })
    if shipment.delivery_contact_name:
        receiver_contact = frappe.get_doc("Contact", shipment.delivery_contact_name)
        
        data['receiver'].update({
            'contact_salutation': receiver_contact.salutation,
            'contact_first_name': receiver_address.get("woocommerce_first_name") or receiver_contact.first_name,
            'contact_last_name': receiver_address.get("woocommerce_last_name") or receiver_contact.last_name,
            'contact_instruction': shipment.get('instruction'),
            'contact_phone': receiver_contact.phone,
            'contact_mobile': receiver_contact.mobile_no,
            'contact_notification': None,
            'contact_email': receiver_contact.email_id,
            'contact_email_notification': None,
            'contact_language': receiver_contact.get("language"),
        })
        
    if shipment.delivery_to_type == "Customer":
        receiver = frappe.get_doc("Customer", shipment.delivery_customer)
        if receiver.customer_type == "Company":
            data['receiver'].update({
                'receiver_type': "G" if receiver.customer_type == "Company" else "P",
                'company': receiver.customer_name,
            })
        else:
            data['receiver'].update({
                'receiver_type': "P",
                'salutation': receiver.salutation,
                'first_name': receiver.get("first_name") or receiver_contact.first_name or receiver.get("full_name"),
                'last_name': receiver.get("last_name") or receiver_contact.last_name
            })
    else:
        frappe.throw( _("Not supported shipping type (other than Customer)") )
        
    for p in shipment.shipment_parcel:
        for c in range(0, p.count):
            data['parcels'].append({
                'length': p.length,
                'width': p.width,
                'height': p.height,
                'weight': p.weight,
                'content': shipment.get('description_of_content'),
                'reference': p.get('reference'),
                'barcode': get_planzer_barcode(shipment_name)
            })
    
    # find delivery date from delivery note
    delivery_note = None
    for dn in shipment.shipment_delivery_note:
        delivery_note = dn.delivery_note
    delivery_date = frappe.get_value("Delivery Note", delivery_note, 'posting_date')
    if delivery_date > shipment.pickup_date:            # delivery cannot be before pickup
        data['delivery_date'] = delivery_date.strftime("%d.%m.%Y")
    else:
        data['delivery_date'] = (shipment.pickup_date + timedelta(days=1)).strftime("%d.%m.%Y")
        
    # options from carrier service
    if shipment.carrier_service:
        for s in shipment.carrier_service.split(","):
            data['options'].append({'service_level_code': s.strip()})
    else:
        # default if no service specified
        data['options'].append({'service_level_code': ""})  # do not fall to default service level code 2020003
    
    # render file
    content = frappe.render_template("erpnextswiss/templates/xml/planzer_shipment.html", data)
    
    # write to temporary file
    local_name = "PAKET_{d}_{n}.csv".format(
        d=datetime.now().strftime("%Y%m%d%H%M%S"),
        n=get_shipment_number(shipment_name)
    )
    local_file = os.path.join("/tmp", local_name)
    f = codecs.open(local_file, "w", encoding="utf-8", errors="ignore")
    f.write(content)
    f.close()

    # move to server
    upload_shipment_file(local_file, "Eingang")

    # remove temporary file
    if not debug:
        os.remove(local_file)

    # create log trace
    log = frappe.get_doc({
        'doctype': 'Planzer Log',
        'title': 'Shipment created',
        'file': local_name,
        'content': content
    })
    log.insert(ignore_permissions=True)
    
    return _("Shipment transmitted")

def upload_shipment_file(file_name, target_path):
    settings = frappe.get_doc("Planzer Settings", "Planzer Settings")
    if not settings.host or not settings.username or not settings.password:
        frappe.throw( _("Planzer Settings are missing connection details (host, username, password)") )

    try:
        with connect_sftp(settings) as sftp:
            with sftp.cd(target_path):          # e.g. "Eingang"
                sftp.put(file_name)            # upload file
                
    except Exception as err:
        frappe.log_error( err, "Planzer Upload Shipment File Failed")
        
    return

def connect_sftp(settings):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = settings.get('host_keys') or None        # keep or None to push None instead of ""  
    
    connection = pysftp.Connection(
            settings.get('host'), 
            port=settings.get('port') or 22,
            username=settings.get('username'), 
            password=get_decrypted_password(settings.get('doctype'), settings.get('name'), 'password', False),
            cnopts=cnopts
        )
    
    return connection

"""
Extract the numeric part of the shipment
"""
def get_shipment_number(shipment_name):
    return ''.join(filter(str.isdigit, shipment_name))
    
def get_planzer_barcode(shipment_name):
    settings = frappe.get_doc("Planzer Settings", "Planzer Settings")
    barcode = "91{customer:06n}{branch:03n}{department:02n}{number:08n}".format(
        customer=cint(settings.customer_no),
        branch=cint(50),
        department=cint(settings.department_no),
        number=cint(get_shipment_number(shipment_name))
    )
    return barcode
    
def get_planzer_qr_code(shipment_name):
    qr_code = "{barcode}{blank}8888888".format(
        barcode=get_planzer_barcode(shipment_name),
        blank=" " * 42
    )
    return qr_code
