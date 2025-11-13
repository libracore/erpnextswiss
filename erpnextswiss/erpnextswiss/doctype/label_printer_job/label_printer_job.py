# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class LabelPrinterJob(Document):
	def after_insert(self):
		printer_doc = frappe.get_doc("Label Printer", self.printer)
		if printer_doc.printing_method == "Direct printing":
			frappe.enqueue("erpnextswiss.erpnextswiss.print_queue.exec_direct_print_job", print_job=self.name)
		else:
			group = getattr(printer_doc, "printer_group", None)
			if group:
				room = "label_printer_group:{group}".format(group=group)
			else:
				# fallback room per-printer
				room = "label_printer:{printer}".format(printer=self.printer)

			job_data = {
				"name": self.name,
				"printer": self.printer,
				"raw_data": self.raw_data,
				"pdf_file": self.pdf_file,
				"creation": self.creation,
			}
			if job_data['pdf_file']:
				job_data['pdf_url'] = frappe.db.get_value("File", job_data['pdf_file'], "file_url")

			try:
				frappe.publish_realtime(event="label_printer_job", message=job_data, room=room)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Label Printer Job: publish_realtime failed")