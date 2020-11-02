# -*- coding: utf-8 -*-
# Copyright (c) 2017-2020, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def is_domain_active(domain):
    domain_settings = frappe.get_doc('Domain Settings')
    active_domains = [d.domain for d in domain_settings.active_domains]
    if domain in active_domains:
        return 1
    else:
        return 0
