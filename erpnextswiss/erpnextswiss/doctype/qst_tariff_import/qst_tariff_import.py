# Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class QSTTariffImport(Document):
	def on_trash(self):
		"""Keep the file as long as a tariff of this import still has rates to load."""
		pending = [tariff for tariff in frappe.get_all("QST Tariff", filters={"tariff_import": self.name}, pluck="name")
		           if frappe.db.exists("QST Tariff Code", {"parent": tariff, "loaded": 0})]
		if pending:
			frappe.throw(_("The tariffs {0} still load their rates from this file").format(", ".join(sorted(pending))))
