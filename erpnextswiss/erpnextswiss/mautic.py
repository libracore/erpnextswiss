# -*- coding: utf-8 -*-
# mautic.py
"""
ERPNext Mautic Integration Module
Synchronisiert Kunden (als Companies), Kontakte und Kampagnen zwischen ERPNext und Mautic
"""

import frappe
import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
from erpnextswiss.scripts.crm_tools import get_primary_customer_address

class MauticAPI:
    """Hauptklasse für die Mautic API Verbindung"""
    
    def __init__(self):
        self.base_url = None
        self.username = None
        self.password = None
        self.load_credentials()
    
    def load_credentials(self):
        """Lädt die Mautic Credentials aus ERPNext Einstellungen"""
        try:
            settings = frappe.get_doc("Mautic Settings")
            self.base_url = (settings.host or "").rstrip('/')
            self.username = settings.username
            self.password = settings.get_password('password')
        except Exception as e:
            frappe.throw("Mautic Credentials nicht gefunden: {0}".format(e))
    
    def test_connection(self):
        """Testet die Verbindung zu Mautic"""
        try:
            response = requests.get(
                "{0}/api/contacts".format(self.base_url),
                auth=HTTPBasicAuth(self.username, self.password),
                params={'limit': 1}
            )
            response.raise_for_status()
            return True, "Verbindung erfolgreich"
        except Exception as e:
            return False, "Verbindungsfehler: {0}\n{1}".format(e, response.text)
    
    # ===== Company API Methods =====
    
    def get_companies(self, limit=100, start=0):
        """Holt Companies aus Mautic"""
        try:
            response = requests.get(
                "{0}/api/companies".format(self.base_url),
                auth=HTTPBasicAuth(self.username, self.password),
                params={'limit': limit, 'start': start}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Abrufen von Mautic Companies: {0}".format(e))
            return None
    
    def create_company(self, company_data):
        """Erstellt eine Company in Mautic"""
        try:
            response = requests.post(
                "{0}/api/companies/new".format(self.base_url),
                auth=HTTPBasicAuth(self.username, self.password),
                json=company_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Erstellen einer Mautic Company: {0}".format(e))
            return None
    
    def update_company(self, company_id, company_data):
        """Aktualisiert eine Company in Mautic"""
        try:
            response = requests.patch(
                "{0}/api/companies/{1}/edit".format(self.base_url, company_id),
                auth=HTTPBasicAuth(self.username, self.password),
                json=company_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Aktualisieren der Mautic Company: {0}".format(e))
            return None
    
    # ===== Contact API Methods =====
    
    def get_contacts(self, limit=100, start=0):
        """Holt Kontakte aus Mautic"""
        try:
            response = requests.get(
                "{0}/api/contacts".format(self.base_url),
                auth=HTTPBasicAuth(self.username, self.password),
                params={'limit': limit, 'start': start}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Abrufen von Mautic Kontakten: {0}".format(e))
            return None
    
    def create_contact(self, contact_data):
        """Erstellt einen Kontakt in Mautic"""
        try:
            response = requests.post(
                "{0}/api/contacts/new".format(self.base_url),
                auth=HTTPBasicAuth(self.username, self.password),
                json=contact_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Erstellen eines Mautic Kontakts: {0}".format(e))
            return None
    
    def update_contact(self, contact_id, contact_data):
        """Aktualisiert einen Kontakt in Mautic"""
        try:
            response = requests.patch(
                "{0}/api/contacts/{1}/edit".format(self.base_url, contact_id),
                auth=HTTPBasicAuth(self.username, self.password),
                json=contact_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Aktualisieren des Mautic Kontakts: {0}".format(e))
            return None
    
    def add_contact_to_company(self, company_id, contact_id):
        """Verknüpft einen Kontakt mit einer Company in Mautic"""
        try:
            response = requests.post(
                "{0}/api/companies/{1}/contact/{2}/add".format(self.base_url, company_id, contact_id),
                auth=HTTPBasicAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Verknüpfen von Kontakt mit Company: {0}".format(e))
            return None
    
    # ===== Campaign API Methods =====
    
    def get_campaigns(self):
        """Holt Kampagnen aus Mautic"""
        try:
            response = requests.get(
                "{0}/api/campaigns".format(self.base_url,
                auth=HTTPBasicAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Abrufen von Mautic Kampagnen: {0}".format(e))
            return None
    
    def add_contact_to_campaign(self, campaign_id, contact_id):
        """Fügt einen Kontakt zu einer Kampagne hinzu"""
        try:
            response = requests.post(
                "{0}/api/campaigns/{1}/contact/{2}/add".format(self.base_url, campaign_id, contact_id),
                auth=HTTPBasicAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error("Fehler beim Hinzufügen zur Kampagne: {0}".format(e))
            return None


def sync_customer_to_mautic(customer_name):
    """Synchronisiert einen ERPNext Kunden als Company zu Mautic"""
    mautic = MauticAPI()
    customer = frappe.get_doc("Customer", customer_name)
    
    # Bereite Company-Daten vor
    company_data = {
        "companyname": customer.customer_name,
        "companyemail": customer.email_id or "",
        "companywebsite": customer.website or "",
    }
    
    customer_address = get_primary_customer_address(customer_name)
    if customer_address:
        company_data.update({
            "companyphone": customer_address.phone or "",
            "companyaddress1": customer_address.address_line1 or "",
            "companycity": customer_address.city or "",
            "companystate": customer_address.state or "",
            "companycountry": customer_address.get("country") or ""
        })
    
    # Prüfe, ob Kunde bereits in Mautic existiert
    mautic_id = customer.get("mautic_id")
    
    if mautic_id:
        result = mautic.update_company(mautic_id, company_data)
        frappe.msgprint("Kunde {0} als Company in Mautic aktualisiert".format(customer_name))
    else:
        result = mautic.create_company(company_data)
        if result and 'company' in result:
            customer.db_set('mautic_id', result['company']['id'])
            frappe.msgprint("Kunde {0} als Company zu Mautic hinzugefügt".format(customer_name))
    
    return result


def sync_contact_to_mautic(contact_name):
    """Synchronisiert einen ERPNext Kontakt zu Mautic"""
    mautic = MauticAPI()
    contact = frappe.get_doc("Contact", contact_name)
    
    # Bereite Kontaktdaten vor
    contact_data = {
        "firstname": contact.first_name or "",
        "lastname": contact.last_name or "",
        "email": contact.email_id or "",
        "phone": contact.phone or contact.mobile_no or "",
        "position": contact.designation or "",
    }
    
    # Hole die Mautic Company ID vom verknüpften Kunden
    company_id = None
    if contact.links:
        for link in contact.links:
            if link.link_doctype == "Customer":
                customer = frappe.get_doc("Customer", link.link_name)
                company_id = customer.get("mautic_company_id")
                if company_id:
                    break
    
    mautic_id = contact.get("mautic_id")
    
    if mautic_id:
        result = mautic.update_contact(mautic_id, contact_data)
        frappe.msgprint("Kontakt {0} in Mautic aktualisiert".format(contact_name))
    else:
        result = mautic.create_contact(contact_data)
        if result and 'contact' in result:
            new_contact_id = result['contact']['id']
            contact.db_set('mautic_id', new_contact_id)
            
            # Verknüpfe Kontakt mit Company, falls vorhanden
            if company_id:
                mautic.add_contact_to_company(company_id, new_contact_id)
            
            frappe.msgprint("Kontakt {0} zu Mautic hinzugefügt".format(contact_name))
    
    # Aktualisiere Company-Verknüpfung, falls sich diese geändert hat
    if mautic_id and company_id:
        mautic.add_contact_to_company(company_id, mautic_id)
    
    return result


def sync_all_customers():
    """Synchronisiert alle ERPNext Kunden als Companies zu Mautic"""
    customers = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name")
    success_count = 0
    error_count = 0
    
    for customer in customers:
        try:
            sync_customer_to_mautic(customer)
            success_count += 1
            frappe.db.commit()
        except Exception as e:
            error_count += 1
            frappe.log_error("Fehler bei Kunde {0}: {1}".format(customer, e))
    
    frappe.msgprint("Kunden-Synchronisation abgeschlossen: {0} erfolgreich, {1} Fehler".format(success_count, error_count))


def sync_all_contacts():
    """Synchronisiert alle ERPNext Kontakte zu Mautic"""
    contacts = frappe.get_all("Contact", filters={"disabled": 0}, pluck="name")
    success_count = 0
    error_count = 0
    
    for contact in contacts:
        try:
            sync_contact_to_mautic(contact)
            success_count += 1
            frappe.db.commit()
        except Exception as e:
            error_count += 1
            frappe.log_error("Fehler bei Kontakt {0}: {1}".format(contact, e))
    
    frappe.msgprint("Kontakt-Synchronisation abgeschlossen: {0} erfolgreich, {1} Fehler".format(success_count, error_count))


def sync_customer_with_contacts(customer_name):
    """Synchronisiert einen Kunden und alle zugehörigen Kontakte"""
    # Erst den Kunden synchronisieren
    sync_customer_to_mautic(customer_name)
    
    # Dann alle verknüpften Kontakte
    contacts = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "link_name": customer_name,
            "parenttype": "Contact"
        },
        pluck="parent"
    )
    
    for contact in contacts:
        try:
            sync_contact_to_mautic(contact)
        except Exception as e:
            frappe.log_error("Fehler bei Kontakt {0}: {1}".format(contact, e))
    
    frappe.msgprint("Kunde {0} mit {1} Kontakten synchronisiert".format(customer_name, len(contacts)))


def import_mautic_campaigns():
    """Importiert Kampagnen aus Mautic nach ERPNext"""
    mautic = MauticAPI()
    campaigns_data = mautic.get_campaigns()
    
    if not campaigns_data or 'campaigns' not in campaigns_data:
        frappe.msgprint("Keine Kampagnen gefunden")
        return
    
    imported = 0
    for campaign_id, campaign in campaigns_data['campaigns'].items():
        try:
            # Prüfe, ob Kampagne bereits existiert
            if not frappe.db.exists("Mautic Campaign", {"mautic_campaign_id": campaign_id}):
                doc = frappe.get_doc({
                    "doctype": "Mautic Campaign",
                    "campaign_name": campaign['name'],
                    "mautic_campaign_id": campaign_id,
                    "description": campaign.get('description', ''),
                    "is_published": campaign.get('isPublished', 0)
                })
                doc.insert()
                imported += 1
        except Exception as e:
            frappe.log_error("Fehler beim Import von Kampagne {0}: {1}".format(campaign_id, e))
    
    frappe.db.commit()
    frappe.msgprint("{0} Kampagnen importiert".format(imported))


@frappe.whitelist()
def test_mautic_connection():
    """API Endpunkt zum Testen der Mautic Verbindung"""
    mautic = MauticAPI()
    success, message = mautic.test_connection()
    return {"success": success, "message": message}


@frappe.whitelist()
def manual_sync_customer(customer_name):
    """API Endpunkt für manuelle Kundensynchronisation"""
    return sync_customer_to_mautic(customer_name)


@frappe.whitelist()
def manual_sync_contact(contact_name):
    """API Endpunkt für manuelle Kontaktsynchronisation"""
    return sync_contact_to_mautic(contact_name)


@frappe.whitelist()
def manual_sync_customer_with_contacts(customer_name):
    """API Endpunkt für Synchronisation eines Kunden mit allen Kontakten"""
    return sync_customer_with_contacts(customer_name)
