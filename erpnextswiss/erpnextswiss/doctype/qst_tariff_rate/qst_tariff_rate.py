# Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSTTariffRate(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("QST Tariff Rate", ["tariff", "code", "income_from"])
