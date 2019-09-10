# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import nowdate
from frappe import _

class InspectionEquipment(Document):
	pass

	
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