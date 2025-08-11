# -*- coding: utf-8 -*-
# Copyright (c) 2018-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
# call the API from
#   /api/method/erpnextswiss.erpnextswiss.caldav.crm_feed?secret=[secret]
#   /api/method/erpnextswiss.erpnextswiss.caldav.todo_feed?secret=[secret]&user=[user]

from icalendar import Calendar, Event, Todo
from datetime import datetime
import frappe
from frappe.utils import cint
from datetime import datetime

def get_crm_feed_content(secret):
    settings = frappe.get_doc("CalDav Feed", "CalDav Feed")
    caldav_secret = settings.get("crm_secret")
    if not caldav_secret:
        return
    if secret != caldav_secret:
        return
    if cint(settings.crm_feed_enabled) == 0:
        return
        
    # initialise calendar
    cal = Calendar()

    # set properties
    cal.add('prodid', '-//libracore business software//libracore//')
    cal.add('version', '2.0')

    # get records
    events = frappe.db.sql("""
        SELECT * 
        FROM `tab{dt}` 
        WHERE 
            `{field}` >= CURDATE()
        ;
    """.format(dt=settings.crm_source, field=settings.crm_source_field), as_dict=True)
    
    # add events
    for erp_event in events:
        event = Event()
        event.add('summary', erp_event.get('name'))
        #start = datetime.strptime(erp_event.get(settings.crm_source_field), "%Y-%m-%d %H:%M:%S")
        event.add('dtstart', erp_event.get(settings.crm_source_field))
        #if erp_event['ends_on']:
        #    event.add('dtend', erp_event['ends_on'])
        event.add('dtstamp', erp_event.get('modified'))
        event.add('description', "{0}\n\r{1}\n\r{2}".format(
            erp_event.get('lead_name') or erp_event.get('customer_name'), 
            erp_event.get('lead_owner') or erp_event.get('account_manager') or erp_event.get('owner'), 
            erp_event['email_id'] or ""))
        # add to calendar
        cal.add_component(event)
        
    return cal

@frappe.whitelist(allow_guest=True)
def crm_feed(secret):
    frappe.local.response.filename = "crm_caldav.ics"
    calendar = get_crm_feed_content(secret)
    if calendar:
        frappe.local.response.filecontent = calendar.to_ical()
    else:
        frappe.local.response.filecontent = "No access"
    frappe.local.response.type = "download"
    return

@frappe.whitelist(allow_guest=True)
def todo_feed(secret, user):
    frappe.local.response.filename = "todo_caldav.ics"
    calendar = get_crm_feed_content(secret)
    if calendar:
        frappe.local.response.filecontent = calendar.to_ical()
    else:
        frappe.local.response.filecontent = "No access"
    frappe.local.response.type = "download"
    return
    
def get_todo_feed_content(secret, user):
    settings = frappe.get_doc("CalDav Feed", "CalDav Feed")
    caldav_secret = settings.get("todo_secret")
    if not caldav_secret:
        return
    if secret != caldav_secret:
        return
    if not frappe.db.exists("User", user):
        return
    if cint(settings.todo_feed_enabled) == 0:
        return
        
    # initialise calendar
    cal = Calendar()

    # set properties
    cal.add('prodid', '-//libracore business software//libracore//')
    cal.add('version', '2.0')
    
    # get todos
    todos = frappe.db.sql("""
        SELECT * 
        FROM `tabToDo` 
        WHERE 
            `date` >= CURDATE()
            AND `owner` = "{user}"
            AND `status` = "Open";
    """.format(user=user), as_dict=True)
    # add todos
    for erp_todo in todos:
        todo = Todo()
        todo.add('uid', erp_todo['name'])
        todo.add('summary', erp_todo['description'])
        todo.add('description', erp_todo['description'])
        todo.add('created', erp_todo['creation'])
        todo.add('last-modified', erp_todo['modified'])
        # add to calendar
        cal.add_component(todo)
        
    return cal
