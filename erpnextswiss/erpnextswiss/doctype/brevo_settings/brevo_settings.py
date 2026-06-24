# -*- coding: utf-8 -*-
# Copyright (c) 2024-2026, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
import requests
import json
from frappe.utils.background_jobs import enqueue
from frappe.utils import cint
from datetime import datetime

API_HOST = "https://api.brevo.com/v3/"

class BrevoSettings(Document):
    def get_api_key(self):
        return get_decrypted_password("Brevo Settings", "Brevo Settings", "api_key", False)

    def enqueue_sync_contacts(self):
        # enqueue pulling contacts


        enqueue("erpnextswiss.erpnextswiss.doctype.brevo_settings.brevo_settings.sync_contacts",
            queue='long',
            timeout=15000)
        return
    
    def get_all_contacts(self, sync=False):
        contacts = []
        limit = 50
        offset = 0
        modified_since = None
        if sync:
            modified_since = self.last_sync
            
        _contact = self.get_contacts(limit, offset, modified_since)
        while _contact:
            for c in _contact:
                contacts.append(c)
                if sync:
                    self.sync_contact(c)
                    
            offset += limit
            _contact = self.get_contacts(limit, offset, modified_since)
        
        self.last_sync = datetime.now()
        self.save()
        frappe.db.commit()
        return "Received {0} contacts".format(len(contacts))
        
    def sync_contact(self, brevo_contact):
        contact_matches = frappe.get_all("Contact", filters={'email_id': brevo_contact.get("email")}, fields=['name'])
        attributes = brevo_contact.get("attributes")
        if len(contact_matches) == 0:
            # create new
            contact = frappe.get_doc({
                'doctype': 'Contact',
                'email_id': brevo_contact.get("email")
            })
            contact.append('email_ids', {
                'email_id': brevo_contact.get("email"),
                'is_primary': 1
            })
        else:
            # update
            contact = frappe.get_doc("Contact", contact_matches[0]['name'])
        
        settings = frappe.get_doc("Brevo Settings", "Brevo Settings")
        
        # map fields
        for m in settings.mapping:
            if m.dt == "Contact":
                contact.update({m.fieldname: attribues.get(m.attribute)})
                    
        contact.flags.ignore_mandatory = True
        contact.flags.ignore_validate = True
        contact.save()
        frappe.db.commit()
        return
            
    def get_contacts(self, limit, offset, modified_since=None):
        parameters = {
            # 'modifiedSince': 'YYYY-MM-DDTHH:mm:ss.SSSZ',
            'limit': '{0}'.format(limit),
            'offset': '{0}'.format(offset),
            #'sort': 'desc',
        }
        if modified_since:
            if type(modified_since) == str:
                modified_since = datetime.strptime(modified_since[:19], "%Y-%m-%d %H:%M:%S")
            parameters['modifiedSince'] = modified_since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
        endpoint = "{0}contacts".format(API_HOST)

        response = requests.get(endpoint, headers=self.get_headers(), params=parameters)
        
        contacts = response.json().get('contacts')      # list of contacts
        
        """ contacts structure:
        {
            'email': 'example@domain.com', 
            'id': 1234, 
            'emailBlacklisted': False, 
            'smsBlacklisted': False, 
            'createdAt': '2024-08-26T16:52:51.853+02:00', 
            'modifiedAt': '2024-08-27T07:30:28.035+02:00', 
            'listIds': [40], 
            'listUnsubscribed': None, 
            'attributes': {
                'TAG': 'Industry', 
                'STATUS': 'Client', 
                'DELIVRABILITE': 'OK', 
                'SOURCE': 'My List', 
                'COMPANY_NAME': 'Example Corp'
            }
        }
        """
        
        return contacts

    def get_all_lists(self, with_folders=False):
        lists = []
        limit = 50
        offset = 0
        _list = self.get_lists(limit, offset)
        while _list:
            for l in _list:
                lists.append(l)
                    
            offset += limit
            _list = self.get_lists(limit, offset)
        
        if cint(with_folders):
            folders = self.get_all_folders()
            for l in lists:
                l['folder_name'] = folders.get(l.get('folderId'))
                
        return lists
    
    def get_lists(self, limit, offset):
        parameters = {
            # 'modifiedSince': 'YYYY-MM-DDTHH:mm:ss.SSSZ',
            'limit': '{0}'.format(limit),
            'offset': '{0}'.format(offset),
            #'sort': 'desc',
        }
        endpoint = "{0}contacts/lists".format(API_HOST)

        response = requests.get(endpoint, headers=self.get_headers(), params=parameters)
        
        lists = response.json().get('lists')      # list of contacts
        
        """
        Structure
            {
                'folderId': 13
    ​​            'id': 42
                'name': "Test List"
                'totalBlacklisted': 0
                'totalSubscribers': 0
                'uniqueSubscribers': 76
            }
        """
        
        return lists
        
    def create_list(self, list_name):
        parameters = {
            'name': list_name
        }
            
        endpoint = "{0}contacts/lists".format(API_HOST)

        headers = self.get_headers()
        headers['content-type'] = 'application/json'
        
        response = requests.post(endpoint, headers=headers, json=parameters)
        
        if response.status_code == 201:
            return {'status': 'Created', 'text': response.text}
        elif response.status_code == 204:
            return {'status': 'Updated', 'text': response.text}
        elif response.status_code == 400:
            return {'status': 'Bad Request', 'text': response.text}
        elif response.status_code == 425:
            return {'status': 'Too Early', 'text': response.text}
        else:
            return {'status': 'Unknown Error', 'text': response.text}
    
    def get_all_folders(self):
        folders = []
        limit = 50
        offset = 0
        _folder = self.get_folders(limit, offset)
        while _folder:
            for f in _folder:
                folders.append(f)
                    
            offset += limit
            _folder = self.get_folders(limit, offset)
        
                
        # restructure so a simple dict
        folder_map = {}
        if folders:
            for f in folders:
                folder_map[f['id']] = f['name']
                
        return folder_map
        
    def get_folders(self, limit, offset):
        parameters = {
            # 'modifiedSince': 'YYYY-MM-DDTHH:mm:ss.SSSZ',
            'limit': '{0}'.format(limit),
            'offset': '{0}'.format(offset),
            #'sort': 'desc',
        }
        endpoint = "{0}contacts/folders".format(API_HOST)

        response = requests.get(endpoint, headers=self.get_headers(), params=parameters)
        
        folders = response.json().get('folders')      # list of contacts
        
        """
        Structure
            {
                'id': 1,
                'name': 'Your first folder',
                'uniqueSubscribers': 0,
                'totalSubscribers': 0,
                'totalBlacklisted': 0}]
            }
        """
            
        return folders
        
    def create_update_contact(self, contact, list_ids=[]):
        contact_doc = frappe.get_doc("Contact", contact)
        if not contact_doc.email_id:
            return
        
        address = None
        if contact_doc.address:
            address = frappe.get_doc("Address", contact_doc.address)
        
        customer = None
        if contact_doc.links and len(contact_doc.links) > 0:
            for c in contact_doc.links:
                if c.link_doctype == "Customer":
                    customer = frappe.get_doc("Customer", c.link_name)
                    break
        
        parameters = {
            'email': contact_doc.email_id,
            'ext_id': contact_doc.name,
            'updateEnabled': True,
            'attributes': {
                'PRENOM': contact_doc.first_name or "", 
                'NOM': contact_doc.last_name or "",
                'EMAIL': contact_doc.email_id or "",
                'COMPANY_NAME': customer.customer_name if customer else "",
                'COMPANY_PHONE': (address.phone or "") if address else "",
                'CITY': address.city if address else "",
                'COUNTRY': address.country if address else "",
                #'TAG': ,
                'STATUS': contact_doc.get("status") or "",
                'DELIVRABILITE': contact_doc.get("deliverability") or "",
                'FROM': contact_doc.get("source") or "",
                'SOURCE': contact_doc.get("event_source") or "",
                'LAST_MODIFIED': contact_doc.modified.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }
        }
        if list_ids and len(list_ids) > 0:
            parameters['listIds'] = list_ids
            
        endpoint = "{0}contacts".format(API_HOST)

        headers = self.get_headers()
        headers['content-type'] = 'application/json'
        
        response = requests.post(endpoint, headers=headers, json=parameters)
        
        if response.status_code == 201:
            return {'status': 'Created', 'text': response.text}
        elif response.status_code == 204:
            return {'status': 'Updated', 'text': response.text}
        elif response.status_code == 400:
            return {'status': 'Bad Request', 'text': response.text}
        elif response.status_code == 425:
            return {'status': 'Too Early', 'text': response.text}
        else:
            return {'status': 'Unknown Error', 'text': response.text}

    def get_headers(self):
        headers = {
            'api-key': self.get_api_key(),
            'accept': 'application/json'
        }
        
        return headers
        
    def delete_contact(self, contact):
        contact_doc = frappe.get_doc("Contact", contact)
        if not contact_doc.email_id:
            return
            
        endpoint = "{0}contacts/{1}".format(API_HOST, contact_doc.email_id)
        
        response = requests.delete(endpoint, headers=self.get_headers())
        
        if  response.status_code == 204:
            return {'status': 'Deleted', 'text': response.text}
        elif response.status_code == 400:
            return {'status': 'Bad Request', 'text': response.text}
        elif response.status_code == 404:
            return {'status': 'Contact Not Found', 'text': response.text}
        elif response.status_code == 425:
            return {'status': 'Too Early', 'text': response.text}
        else:
            return {'status': 'Unknown Error', 'text': response.text}
    
    def get_contact_campaign_stats(self, contact_email):
        parameters = {
            # 'modifiedSince': 'YYYY-MM-DDTHH:mm:ss.SSSZ',
            'start_date': '2020-01-01',
            'end_date': '2024-12-31',
            #'sort': 'desc',
        }
        endpoint = "{0}contacts/{1}/campaignStats".format(API_HOST, contact_email)
        
        response = requests.get(endpoint, headers=self.get_headers(), params=parameters)
        
        campaign_stats = response.json()       # campaign stats
        
        """
        Structure
            {'messagesSent': [{'campaignId': 77,
               'eventTime': '2024-12-10T16:30:47.489+01:00'}],
             'softBounces': [{'campaignId': 77,
               'eventTime': '2024-12-10T16:32:08.000+01:00'}]}
        """
        
        # restructure
        campaigns = {}
        
        self.update_campaign_parameter(campaigns, campaign_stats, 'messagesSent')
        self.update_campaign_parameter(campaigns, campaign_stats, 'softBounces')
        self.update_campaign_parameter(campaigns, campaign_stats, 'hardBounces')
        self.update_campaign_parameter(campaigns, campaign_stats, 'complaints')
        self.update_campaign_parameter(campaigns, campaign_stats, 'opened')
        self.update_campaign_parameter(campaigns, campaign_stats, 'clicked')
        self.update_campaign_parameter(campaigns, campaign_stats, 'delivered')
                
        campaigns_html = frappe.render_template("amf/master_crm/doctype/brevo/contact_stats.html", {'campaigns': campaigns})
        
        return {'campaigns': campaigns, 'html': campaigns_html}
    
    def update_campaign_parameter(self, campaigns, campaign_stats, parameter):
        for p in (campaign_stats.get(parameter) or []):
            if p.get("campaignId") not in campaigns:
                campaigns[p.get("campaignId")] = {parameter: p.get("eventTime")}
            else:
                campaigns[p.get("campaignId")][parameter] = p.get("eventTime")
        return
        
    def get_all_campaigns(self):
        campaigns = []
        limit = 50
        offset = 0
        _list = self.get_campaigns(limit, offset)
        while _list:
            for l in _list:
                campaigns.append(l)
                    
            offset += limit
            _list = self.get_campaigns(limit, offset)
        
        self.update_campaigns(campaigns)
        
        return campaigns
    
    def update_campaigns(self, campaigns):
        for campaign in campaigns:
            if not frappe.db.exists("Brevo Campaign", campaign.get("id")):
                new_campaign = frappe.get_doc({
                    'doctype': 'Brevo Campaign',
                    'title': campaign.get("name"),
                    'status': campaign.get("status")
                })
                new_campaign.insert()
            else:
                frappe.db.set_value("Brevo Campaign", campaign.get("id"), "status", campaign.get("status"))
            frappe.db.commit()
            
        return
        
    def get_campaigns(self, limit, offset):
        parameters = {
            'limit': '{0}'.format(limit),
            'offset': '{0}'.format(offset),
        }
        endpoint = "{0}emailCampaigns".format(API_HOST)

        response = requests.get(endpoint, headers=self.get_headers(), params=parameters)
        
        if response.status_code != 200:
            frappe.throw("Error {0}: {1}".format(response.status_code, response.text))

        campaigns = response.json().get('campaigns')      # list of campaigns
        
        """
        Structure
            {'id': 3,
           'name': '2023',
           'type': 'classic',
           'status': 'sent',
           'testSent': True,
           'header': '[DEFAULT_HEADER]',
           'footer': 'EXISTS',
           'sender': {'name': 'A',
            'id': 2,
            'email': 'info@example.com'},
           'replyTo': '[DEFAULT_REPLY_TO]',
           'toField': '',
           'previewText': 'Save the date',
           'tag': '2023',
           'inlineImageActivation': True,
           'mirrorActive': True,
           'recipients': {'lists': [2, 3], 'exclusionLists': []},
           'statistics': {'globalStats': {'uniqueClicks': 0,
             'clickers': 0,
             'complaints': 0,
             'delivered': 0,
             'sent': 0,
             'softBounces': 0,
             'hardBounces': 0,
             'uniqueViews': 0,
             'unsubscriptions': 0,
             'viewed': 0,
             'trackableViews': 0,
             'trackableViewsRate': 0,
             'estimatedViews': 0},
            'campaignStats': [{'listId': 2,
              'uniqueClicks': 0,
              'clickers': 0,
              'complaints': 0,
              'delivered': 1,
              'sent': 1,
              'softBounces': 0,
              'hardBounces': 0,
              'uniqueViews': 1,
              'trackableViews': 1,
              'unsubscriptions': 0,
              'viewed': 3,
              'deferred': 0},
             {'listId': 3,
              'uniqueClicks': 15,
              'clickers': 27,
              'complaints': 0,
              'delivered': 2058,
              'sent': 2341,
              'softBounces': 98,
              'hardBounces': 233,
              'uniqueViews': 226,
              'trackableViews': 226,
              'unsubscriptions': 10,
              'viewed': 331,
              'deferred': 103}],
            'mirrorClick': 13,
            'remaining': 0,
            'linksStats': {},
           'htmlContent': '(...html..)'
           'subject': '2023',
           'scheduledAt': '2023-02-16T16:00:00.000+01:00',
           'createdAt': '2023-02-16T10:11:37.000+01:00',
           'modifiedAt': '2023-02-16T13:29:22.000+01:00',
           'shareLink': '',
           'sentDate': '2023-02-16T17:37:49.000+01:00',
           'sendAtBestTime': False,
           'abTesting': False}
        """
        
        return campaigns
        
@frappe.whitelist()
def fetch_contacts():
    brevo = frappe.get_doc("Brevo Settings", "Brevo Settings")
    return brevo.get_all_contacts()
    
def sync_contacts():
    brevo = frappe.get_doc("Brevo Settings", "Brevo Settings")
    brevo.get_all_contacts(sync=True)
    return
    
@frappe.whitelist()
def fetch_lists(with_folders=False):
    brevo = frappe.get_doc("Brevo Settings", "Brevo Settings")
    return brevo.get_all_lists(with_folders)

@frappe.whitelist()
def create_update_contact(contact, list_ids=[]):
    if type(list_ids) == str:
        list_ids = json.loads(list_ids)
    brevo = frappe.get_doc("Brevo Settings", "Brevo Settings")
    return brevo.create_update_contact(contact, list_ids)

@frappe.whitelist()
def fetch_campaigns():
    brevo = frappe.get_doc("Brevo Settings", "Brevo Settings")
    return brevo.get_all_campaigns()

@frappe.whitelist()
def fetch_contact_stats(contact_email):
    brevo = frappe.get_doc("Brevo Settings", "Brevo Settings")
    return brevo.get_contact_campaign_stats(contact_email)
