# -*- coding: utf-8 -*-
# Copyright (c) 2019, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class NonConformityReport8D(Document):
	def before_save(self):
		if self.d1_complete == 0:
			self.status = "New"
			return
		if self.d2_complete == 0:
			self.status = "D2"
			return
		if self.d3_complete == 0:
			self.status = "D3"
			return
		if self.d4_complete == 0:
			self.status = "D4"
			return
		if self.d5_complete == 0:
			self.status = "D5"
			return
		if self.d6_complete == 0:
			self.status = "D6"
			return
		if self.d7_complete == 0:
			self.status = "D7"
			return
		if self.d8_complete == 0:
			self.status = "D8"
		else:
			self.status = "Completed"