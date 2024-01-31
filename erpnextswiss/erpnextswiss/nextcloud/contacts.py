# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import erpnextswiss.erpnextswiss.nextcloud.carddav as carddav
import hashlib
import frappe
from frappe.utils.password import get_decrypted_password
from frappe.utils import cint
from datetime import datetime

def send_contact_to_nextcloud(contact, event=None, debug=False):
    # fetch settings
    settings = frappe.get_doc("NextCloud Settings", "NextCloud Settings")
    # leave if nextcloud is not enabled
    if not cint(settings.enabled) or not cint(settings.sync_contacts):
        return
    
    # if the paramter was a string, try to load the object
    if type(contact) == str and frappe.db.exists("Contact", contact):
        contact = frappe.get_doc("Contact", contact)
    
    try:
        contact_data = contact.as_dict()
    except Exception as err:
        frappe.throw(err)
        
    if contact.address:
        contact_data.update(frappe.get_doc("Address", contact.address).as_dict())
    
    contact_data['uid'] = hashlib.md5((contact.name.lower()).encode("utf-8")).hexdigest()
    if not contact_data.get('full_name'):
        contact_data['full_name'] = "{0} {1}".format(contact.first_name or "", contact.last_name or "")
        
    if type(contact.modified) == str:
        ts = datetime.strptime(contact.modified[:19], "%Y-%m-%d %H:%M:%S").strftime("%Y%m%dT%H%M%SZ")
    else:
        ts = contact.modified.strftime("%Y%m%dT%H%M%SZ")
    contact_data['ts'] = ts
    
    # add notes
    contact_data['note'] = contact.get("remarks") or contact.get("notes") or contact.get("notizen")
    if contact_data['note']:
        # remove line breaks
        contact_data['note'] = contact_data['note'].replace("\n", "").replace("\r", "")
        
    vcard = frappe.render_template("erpnextswiss/erpnextswiss/nextcloud/vcard.html", contact_data)
    
    if debug:
        print("{0}".format(vcard))

    upload_card(vcard, "{0}.vcf".format(contact_data['uid']))
    
    return

def delete_contact_from_nextcloud(contact, event=None):
    # fetch settings
    settings = frappe.get_doc("NextCloud Settings", "NextCloud Settings")
    # leave if nextcloud is not enabled
    if not cint(settings.enabled) or not cint(settings.sync_contacts):
        return
    
    # if the paramter was a string, try to load the object
    if type(contact) == str and frappe.db.exists("Contact", contact):
        contact = frappe.get_doc("Contact", contact)
    
    uid = hashlib.md5((contact.name.lower()).encode("utf-8")).hexdigest()
        
    delete_card("{0}.vcf".format(uid))
    
    return
    
def connect_dav():
    settings = frappe.get_doc("NextCloud Settings", "NextCloud Settings")
    
    url = "{host}/remote.php/dav/addressbooks/users/{user}/{addressbook}/".format(
        host=settings.host, 
        user=settings.user, 
        addressbook=settings.address_book
    )
    
    dav = carddav.PyCardDAV( 
        url, 
        user=settings.user, 
        passwd=get_decrypted_password("NextCloud Settings", "NextCloud Settings", 'password', False), 
        auth="basic",
        verify=True if cint(settings.verify_ssl) else False,
        write_support=True
    )
    
    return dav
    
def download_addressbook():
    dav = connect_dav()
    abook  = dav.get_abook()
    vcards = ""

    for href, etag in abook.items():
        card = dav.get_vcard( href )
        vcards += card.decode('utf-8') + '\n'
    
    return vcards

def upload_card(card, target):
    dav = connect_dav()

    try:
        dav.update_vcard(card, target, None)
        
    except Exception as e:
        frappe.log_error(e, "Upload vcard to nextcloud failed")
    
    return

def delete_card(target):
    dav = connect_dav()

    try:
        dav.delete_vcard(target, None)
        
    except Exception as e:
        frappe.log_error(e, "Delete vcard from nextcloud failed")
    
    return
