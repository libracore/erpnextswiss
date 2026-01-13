# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class LabelPrinterJob(Document):
	_enqueue_failed_to_waiting = False

	# Trigger to run direct printing jobs in the background on creation
	def after_insert(self):
		frappe.db.commit()
		printer_doc = frappe.get_doc("Label Printer", self.printer)
		if printer_doc.printing_method == "Direct printing":
			frappe.enqueue("erpnextswiss.erpnextswiss.print_queue.exec_direct_print_job", print_job=self.name)

	# Trigger to run direct printing jobs again if status is set from Failed to Waiting (by "Retry" button or manually)
	def before_save(self):
		# Clear status message for waiting jobs
		if self.status == "Waiting":
			self.status_message = ''

		# Only proceed for updates, not new docs
		if self.get("__islocal"):
			return

		# Only relevant for jobs with direct printing
		printing_method = frappe.db.get_value("Label Printer", self.printer, "printing_method")
		if printing_method != "Direct printing":
			return

		# Fetch previous status from DB
		prev_status = frappe.db.get_value("Label Printer Job", self.name, "status")

		if prev_status == "Failed" and self.status == "Waiting":
			# mark to enqueue after commit (otherwise the job status might still be "Failed" when the job runs)
			self._enqueue_failed_to_waiting = True

	# Enqueue direct printing job, if triggered above
	def on_update(self):
		frappe.db.commit()
		if getattr(self, "_enqueue_failed_to_waiting", False):
			frappe.enqueue("erpnextswiss.erpnextswiss.print_queue.exec_direct_print_job", print_job=self.name)
			self._enqueue_failed_to_waiting = False
