# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import pdfkit, os, frappe
from frappe.model.document import Document

class LabelPrinter(Document):
	pass

# creates a pdf based on a label printer and a html content
def create_pdf(label_printer, content):
	# create temporary file
	fname = os.path.join("/tmp", "frappe-pdf-{0}.pdf".format(frappe.generate_hash()))
	
	options = { 
		'page-width': '{0}mm'.format(label_printer.width), 
		'page-height': '{0}mm'.format(label_printer.height), 
		'margin-top': '0mm',
		'margin-bottom': '0mm',
		'margin-left': '0mm',
		'margin-right': '0mm' }

	html_content = """
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="utf-8">
	</head>
	<body>
		{content}
	<body>
	</html>
	""".format(content=content)
	
	pdfkit.from_string(html_content, fname, options=options or {})
	
	with open(fname, "rb") as fileobj:
		filedata = fileobj.read()
	
	cleanup(fname)
	
	return filedata

def cleanup(fname):
	if os.path.exists(fname):
		os.remove(fname)
	return
	
@frappe.whitelist()
def download_label(label_reference, content):
	label = frappe.get_doc("Label Printer", label_reference)
	frappe.local.response.filename = "{name}.pdf".format(name=label_reference.replace(" ", "-").replace("/", "-"))
	frappe.local.response.filecontent = create_pdf(label, content)
	frappe.local.response.type = "download"
