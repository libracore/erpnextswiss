# Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSTTariff(Document):
	def autoname(self):
		self.name = "QST-{0}-{1}-{2}".format(self.canton, self.year, frappe.utils.getdate(self.creation_date).strftime("%Y%m%d"))

	def on_trash(self):
		frappe.db.delete("QST Tariff Rate", {"tariff": self.name})
