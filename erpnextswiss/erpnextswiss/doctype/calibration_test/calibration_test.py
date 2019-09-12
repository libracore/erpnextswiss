# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

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