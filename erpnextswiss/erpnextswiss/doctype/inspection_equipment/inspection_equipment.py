# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate, add_months
from frappe import _

class InspectionEquipment(Document):
	def validate(self):
		if not self.last_calibration:
			self.last_calibration = nowdate()
		
		self.next_calibration = add_months(self.last_calibration, self.calibration_interval)
		
		if self.status == 'Calibrated':
			if self.next_calibration < nowdate():
				self.status = 'To Calibrate'
				
		if self.status == 'To Calibrate':
			if self.next_calibration >= nowdate():
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