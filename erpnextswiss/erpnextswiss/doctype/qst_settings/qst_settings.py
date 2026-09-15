# Copyright (c) 2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSTSettings(Document):
	def validate(self):
		if not self.enabled:
			return
		for fieldname in ("qst_component", "correction_component"):
			if frappe.db.get_value("Salary Component", self.get(fieldname), "type") != "Deduction":
				frappe.throw(frappe._("{0} must be a deduction").format(self.meta.get_label(fieldname)))
		used = frappe.get_all("Salary Detail", filters={"parenttype": "Salary Structure", "salary_component": ("in", [self.qst_component, self.correction_component])}, pluck="parent", distinct=True)
		if used:
			frappe.msgprint(frappe._("Quellensteuer components are calculated automatically, please remove them from these salary structures: {0}").format(", ".join(used)))
