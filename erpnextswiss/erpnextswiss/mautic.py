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
            frappe.throw(f"Mautic Credentials nicht gefunden: {str(e)}")
    
    def test_connection(self):
        """Testet die Verbindung zu Mautic"""
        try:
            response = requests.get(
                f"{self.base_url}/api/contacts",
                auth=HTTPBasicAuth(self.username, self.password),
                params={'limit': 1}
            )
            response.raise_for_status()
            return True, "Verbindung erfolgreich"
        except Exception as e:
            return False, f"Verbindungsfehler: {str(e)}\n{response.text}"
    
    # ===== Company API Methods =====
    
    def get_companies(self, limit=100, start=0):
        """Holt Companies aus Mautic"""
        try:
            response = requests.get(
                f"{self.base_url}/api/companies",
                auth=HTTPBasicAuth(self.username, self.password),
                params={'limit': limit, 'start': start}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Abrufen von Mautic Companies: {str(e)}")
            return None
    
    def create_company(self, company_data):
        """Erstellt eine Company in Mautic"""
        try:
            response = requests.post(
                f"{self.base_url}/api/companies/new",
                auth=HTTPBasicAuth(self.username, self.password),
                json=company_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Erstellen einer Mautic Company: {str(e)}")
            return None
    
    def update_company(self, company_id, company_data):
        """Aktualisiert eine Company in Mautic"""
        try:
            response = requests.patch(
                f"{self.base_url}/api/companies/{company_id}/edit",
                auth=HTTPBasicAuth(self.username, self.password),
                json=company_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Aktualisieren der Mautic Company: {str(e)}")
            return None
    
    # ===== Contact API Methods =====
    
    def get_contacts(self, limit=100, start=0):
        """Holt Kontakte aus Mautic"""
        try:
            response = requests.get(
                f"{self.base_url}/api/contacts",
                auth=HTTPBasicAuth(self.username, self.password),
                params={'limit': limit, 'start': start}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Abrufen von Mautic Kontakten: {str(e)}")
            return None
    
    def create_contact(self, contact_data):
        """Erstellt einen Kontakt in Mautic"""
        try:
            response = requests.post(
                f"{self.base_url}/api/contacts/new",
                auth=HTTPBasicAuth(self.username, self.password),
                json=contact_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Erstellen eines Mautic Kontakts: {str(e)}")
            return None
    
    def update_contact(self, contact_id, contact_data):
        """Aktualisiert einen Kontakt in Mautic"""
        try:
            response = requests.patch(
                f"{self.base_url}/api/contacts/{contact_id}/edit",
                auth=HTTPBasicAuth(self.username, self.password),
                json=contact_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Aktualisieren des Mautic Kontakts: {str(e)}")
            return None
    
    def add_contact_to_company(self, company_id, contact_id):
        """Verknüpft einen Kontakt mit einer Company in Mautic"""
        try:
            response = requests.post(
                f"{self.base_url}/api/companies/{company_id}/contact/{contact_id}/add",
                auth=HTTPBasicAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Verknüpfen von Kontakt mit Company: {str(e)}")
            return None
    
    # ===== Campaign API Methods =====
    
    def get_campaigns(self):
        """Holt Kampagnen aus Mautic"""
        try:
            response = requests.get(
                f"{self.base_url}/api/campaigns",
                auth=HTTPBasicAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Abrufen von Mautic Kampagnen: {str(e)}")
            return None
    
    def add_contact_to_campaign(self, campaign_id, contact_id):
        """Fügt einen Kontakt zu einer Kampagne hinzu"""
        try:
            response = requests.post(
                f"{self.base_url}/api/campaigns/{campaign_id}/contact/{contact_id}/add",
                auth=HTTPBasicAuth(self.username, self.password)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            frappe.log_error(f"Fehler beim Hinzufügen zur Kampagne: {str(e)}")
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
        frappe.msgprint(f"Kunde {customer_name} als Company in Mautic aktualisiert")
    else:
        result = mautic.create_company(company_data)
        if result and 'company' in result:
            customer.db_set('mautic_id', result['company']['id'])
            frappe.msgprint(f"Kunde {customer_name} als Company zu Mautic hinzugefügt")
    
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
        frappe.msgprint(f"Kontakt {contact_name} in Mautic aktualisiert")
    else:
        result = mautic.create_contact(contact_data)
        if result and 'contact' in result:
            new_contact_id = result['contact']['id']
            contact.db_set('mautic_id', new_contact_id)
            
            # Verknüpfe Kontakt mit Company, falls vorhanden
            if company_id:
                mautic.add_contact_to_company(company_id, new_contact_id)
            
            frappe.msgprint(f"Kontakt {contact_name} zu Mautic hinzugefügt")
    
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
            frappe.log_error(f"Fehler bei Kunde {customer}: {str(e)}")
    
    frappe.msgprint(f"Kunden-Synchronisation abgeschlossen: {success_count} erfolgreich, {error_count} Fehler")


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
            frappe.log_error(f"Fehler bei Kontakt {contact}: {str(e)}")
    
    frappe.msgprint(f"Kontakt-Synchronisation abgeschlossen: {success_count} erfolgreich, {error_count} Fehler")


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
            frappe.log_error(f"Fehler bei Kontakt {contact}: {str(e)}")
    
    frappe.msgprint(f"Kunde {customer_name} mit {len(contacts)} Kontakten synchronisiert")


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
            frappe.log_error(f"Fehler beim Import von Kampagne {campaign_id}: {str(e)}")
    
    frappe.db.commit()
    frappe.msgprint(f"{imported} Kampagnen importiert")


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
