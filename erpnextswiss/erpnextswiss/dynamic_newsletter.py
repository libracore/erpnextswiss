# -*- coding: utf-8 -*-
# Copyright (c) 2018-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from frappe.email.queue import send
import frappe
from frappe.utils.background_jobs import enqueue
from frappe import _

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
        frappe.log_error( _("Sending failed: unable to load newsletter {0}").format(newsletter),
            _("Dynamic newsletter"))

    # read recipient lists
    for email_group in newsletter.email_group:
        # get recipient information
        recipients = frappe.get_all('Email Group Member', filters=[['email_group', '=', email_group.email_group], ['unsubscribed', '=', 0]], fields=['email'])

        if recipients:
            for recipient in recipients:
                contacts = frappe.get_all('Contact', filters=[['email_id', '=', recipient.email]], fields=['name'])
                if contacts:
                    contact = frappe.get_doc("Contact", contacts[0]['name'])
                    # prepare newsletter
                    try:
                        subject = newsletter.subject
                        if contact.first_name:
                            message = newsletter.message.replace(u"{{ first_name }}", contact.first_name)
                        else:
                            message = newsletter.message.replace(u"{{ first_name }}", "")
                        if contact.last_name:
                            message = message.replace(u"{{ last_name }}", contact.last_name)
                        else:
                            message = message.replace(u"{{ last_name }}", "")
                        if contact.salutation:
                            message = message.replace(u"{{ salutation }}", contact.salutation)
                        else:
                            message = message.replace(u"{{ salutation }}", "")
                        if contact.department:
                            message = message.replace(u"{{ department }}", contact.department)
                        else:
                            message = message.replace(u"{{ department }}", "")
                        if contact.designation:
                            message = message.replace(u"{{ designation }}", contact.designation)
                        else:
                            message = message.replace(u"{{ designation }}", "")
                        try:
                            if contact.letter_salutation:
                                message = message.replace(u"{{ letter_salutation }}", contact.letter_salutation)
                            else:
                                message = message.replace(u"{{ letter_salutation }}", "")
                        except:
                            message = message
                        try:
                            if contact.briefanrede:
                                message = message.replace(u"{{ briefanrede }}", contact.briefanrede)
                            else:
                                message = message.replace(u"{{ briefanrede }}", "")
                        except:
                            message = message
                        # send mail
                        send(
                            recipients=recipient.email,
                            sender=newsletter.send_from,
                            subject=subject,
                            message=message,
                            reply_to=newsletter.send_from
                        )
                    except Exception as err:
                        frappe.log_error( u"Sending newsletter {0} to {1} failed: {2}.".format(newsletter.name, recipient.email, unicode(err)),
                            _("Dynamic newsletter"))

    # mark newsletter as sent
    newsletter.email_sent = 1
    newsletter.save()

    return
