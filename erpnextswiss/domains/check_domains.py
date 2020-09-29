# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def get_active_domains(domain):
	domain_settings = frappe.get_doc('Domain Settings')
	active_domains = [d.domain for d in domain_settings.active_domains]
	if domain in active_domains:
		return True
	else:
		return False