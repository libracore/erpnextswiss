# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate, getdate
from frappe import _

class CalibrationTest(Document):
	def validate(self):
		if self.calibration_test_set and not self.test_plan_items:
			test_plan_items = frappe.get_doc("Calibration Test Set", self.calibration_test_set)
			for test in test_plan_items.test_plan:
				row = self.append('test_plan_items', {})
				row.test_based_on = test.test_based_on
				row.designation = test.designation
				row.operating_instructions = test.operating_instructions
				row.nominal_value = test.nominal_value
				row.otg = test.otg
				row.utg = test.utg
				row.actual_value = test.actual_value
				row.remarks = test.remarks
				row.inspection_decision_ok = test.inspection_decision_ok
				
	def on_submit(self):
		result = True
		for test in self.test_plan_items:
			if test.inspection_decision_ok == 0:
				result = False
				
		
		inspection_equipment = frappe.get_doc("Inspection Equipment", self.inspection_equipment)
		inspection_equipment.last_calibration = getdate(nowdate())
		#test passed
		if result:
			inspection_equipment.status = 'Calibrated'
		#test failed
		else:
			inspection_equipment.status = 'To Calibrate'
			
		inspection_equipment.save()
		