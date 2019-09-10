# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate, add_months, getdate
from frappe import _

class InspectionEquipment(Document):
	def validate(self):
		if not self.last_calibration:
			self.last_calibration = nowdate()
		
		self.next_calibration = add_months(getdate(self.last_calibration), self.calibration_interval)
		
		if self.status == 'Calibrated':
			if getdate(self.next_calibration) < getdate(nowdate()):
				self.status = 'To Calibrate'
				
		if self.status == 'To Calibrate':
			if getdate(self.next_calibration) >= getdate(nowdate()):
				self.status = 'Calibrated'

def check_calibration_status():
	equipment_to_update_status = frappe.db.sql("""
												SELECT `name`
												FROM `tabInspection Equipment`
												WHERE
													`status` = 'Calibrated'
													AND `next_calibration` < CURDATE()""", as_list=True)
	if equipment_to_update_status:
		for equipment in equipment_to_update_status:
			equipment = frappe.get_doc("Inspection Equipment", equipment[0])
			equipment.status = 'To Calibrate'
			equipment.save()
			equipment.add_comment(comment_type='Comment', text=_("This Inspection Equipment has to be calibrated."))
			
@frappe.whitelist()
def create_transaction(inspection_equipment, employee, status):
	transaction = frappe.new_doc("Inspection Equipment Transaction")
	transaction.inspection_equipment = inspection_equipment
	transaction.date = nowdate()
	transaction.employee = employee
	if status == 'On Stock':
		transaction.current_status = 'On Stock'
		transaction.new_status = 'Taken'
	else:
		transaction.current_status = 'Taken'
		transaction.new_status = 'On Stock'
	transaction.save()
	return transaction.name