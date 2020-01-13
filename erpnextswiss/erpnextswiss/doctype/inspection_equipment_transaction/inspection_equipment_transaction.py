# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class InspectionEquipmentTransaction(Document):
	def on_submit(self):
		equipment = frappe.get_doc("Inspection Equipment", self.inspection_equipment)
		if self.current_status == 'On Stock':
			employee = frappe.get_doc("Employee", self.employee)
			equipment.transaction_status = "Taken"
			equipment.taken_by = employee.employee_name
			equipment.save()
		else:
			equipment.transaction_status = "On Stock"
			equipment.taken_by = ''
			equipment.save()