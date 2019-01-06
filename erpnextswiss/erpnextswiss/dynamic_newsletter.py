# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from frappe.email.queue import send
import frappe

# send newsletter with dynamic content
@frappe.whitelist()
def enqueue_send_dynamic_newsletter(newsletter):
    # enqueue sending newsletter (potential long worker)
    kwargs={
        'newsletter': newsletter
    }
        
    enqueue("erpnextswiss.erpnextswiss.dynamic_newsletter.send_dynamic_newsletter",
        queue='long',
        timeout=15000,
        **kwargs)
    return

def send_dynamic_newsletter(newsletter):
    # load newsletter
    try:
        newsletter = frappe.get_doc('Newsletter', newsletter)
    except:
        frappe.log_error( _("Dynamic newsletter"), _("Sending failed: unable to load newsletter {0}").format(newsletter))
    
    # read recipient lists
    for group_name in newsletter.email_group:
        # get recipient information
        recipients = frappe.get_all('Email Group Member', filters={'email_group': group_name, 'unsubscribed': 0}, fields=['email'])
        
        if recipients:
            for recipient in recipients:
                contacts = frappe.get_all('Contact', filters={'email_id': recipient.email}, fields=['first_name', 'last_name'])
                if contacts:
                    # prepare newsletter
                    subject = newsletter.subject
                    message = newsletter.message.replace("{{ first_name }}", contacts[0]['first_name']).replace("{{ last_name }}", contacts[0]['last_name'])
                    # send mail
                    send(
                        recipients=recipient.email,
                        sender=newsletter.send_from,
                        subject=subject,
                        message=message,
                        reply_to=newsletter.send_from
                    )
    
    # mark newsletter as sent
    newsletter.email_sent = 1
    newsletter.save()
    
    return
