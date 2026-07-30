# -*- coding: utf-8 -*-
# Copyright (c) 2018-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
# call the API from
#   /api/method/erpnextswiss.erpnextswiss.caldav.crm_feed?secret=[secret]
#   /api/method/erpnextswiss.erpnextswiss.caldav.todo_feed?secret=[secret]&user=[user]

import hmac

import frappe
from icalendar import Calendar, Event, Todo
from frappe.utils import cint, today


def _secret_matches(provided, expected):
    return bool(expected) and hmac.compare_digest(
        str(provided or "").encode("utf-8"),
        str(expected).encode("utf-8"),
    )


def get_crm_feed_content(secret):
    settings = frappe.get_doc("CalDav Feed", "CalDav Feed")
    caldav_secret = settings.get("crm_secret")
    if not _secret_matches(secret, caldav_secret):
        return
    if cint(settings.crm_feed_enabled) == 0:
        return

    source = settings.crm_source
    source_field = settings.crm_source_field
    if source not in {"Lead", "Customer"}:
        return
    source_meta = frappe.get_meta(source)
    if not source_field or not source_meta.has_field(source_field):
        return

    # initialise calendar
    cal = Calendar()

    # set properties
    cal.add('prodid', '-//libracore business software//libracore//')
    cal.add('version', '2.0')

    event_fields = [
        "name",
        source_field,
        "modified",
        "owner",
        "email_id",
    ]
    if source == "Lead":
        event_fields.extend(["lead_name", "lead_owner"])
    else:
        event_fields.extend(["customer_name", "account_manager"])
    event_fields = list(dict.fromkeys(event_fields))

    events = frappe.get_all(
        source,
        filters=[[source_field, ">=", today()]],
        fields=event_fields,
    )

    # add events
    for erp_event in events:
        event = Event()
        event.add('summary', erp_event.get('name'))
        event.add('dtstart', erp_event.get(source_field))
        #if erp_event['ends_on']:
        #    event.add('dtend', erp_event['ends_on'])
        event.add('dtstamp', erp_event.get('modified'))
        event.add('description', "{0}\n\r{1}\n\r{2}".format(
            erp_event.get('lead_name') or erp_event.get('customer_name') or "",
            erp_event.get('lead_owner') or erp_event.get('account_manager') or erp_event.get('owner') or "",
            erp_event.get('email_id') or ""))
        # add to calendar
        cal.add_component(event)

    return cal


@frappe.whitelist(allow_guest=True, methods=["GET"])
def crm_feed(secret):
    frappe.local.response.filename = "crm_caldav.ics"
    calendar = get_crm_feed_content(secret)
    if calendar:
        frappe.local.response.filecontent = calendar.to_ical()
    else:
        frappe.local.response.filecontent = "No access"
    frappe.local.response.type = "download"
    return


@frappe.whitelist(allow_guest=True, methods=["GET"])
def todo_feed(secret, user):
    frappe.local.response.filename = "todo_caldav.ics"
    calendar = get_todo_feed_content(secret, user)
    if calendar:
        frappe.local.response.filecontent = calendar.to_ical()
    else:
        frappe.local.response.filecontent = "No access"
    frappe.local.response.type = "download"
    return


def get_todo_feed_content(secret, user):
    settings = frappe.get_doc("CalDav Feed", "CalDav Feed")
    caldav_secret = settings.get("todo_secret")
    if not _secret_matches(secret, caldav_secret):
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
    
    todos = frappe.get_all(
        "ToDo",
        filters={
            "date": [">=", today()],
            "owner": user,
            "status": "Open",
        },
        fields=["name", "description", "creation", "modified"],
    )
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
