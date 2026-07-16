# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "ERPNextSwiss",
			"color": "#92d050",
			"icon": "icon erpnextswiss-blue",
			"type": "module",
			"label": _("Schweizer Buchhaltung"),
            "description": _("Schweizer Banking, QR-Rechnung, MwSt und E-Rechnung")
		}
	]
