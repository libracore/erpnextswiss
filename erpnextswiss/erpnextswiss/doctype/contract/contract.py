# -*- coding: utf-8 -*-
# Copyright (c) 2018-2026, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe.utils import add_days, add_months, getdate, today, date_diff

class Contract(Document):
	pass

@frappe.whitelist()
def get_next_date(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)
	
	frequency = doc.get("frequency")
	base_date = doc.get("last_execution_date") or doc.get("start_date")
	if not base_date or not frequency:
		return None
		
	base_date = getdate(base_date)

	if frequency in ["Daily", "Weekly"]:
		# Map interval in days
		interval_days = days_mapper(frequency)
		next_date = add_days(base_date, interval_days)
	else:
		# Map interval in months
		interval_months = months_mapper(frequency)
		next_date = add_months(base_date, interval_months)
	
	return next_date

def days_mapper(frequency):
	"""Maps contract frequency to number of days."""
	mapping = {
		"Daily": 1,
		"Weekly": 7
	}
	return mapping.get(frequency, 1)

def months_mapper(frequency):
	mapping = {
		"Monthly": 1,
		"Quarterly": 3,
		"Half-Yearly": 6,
		"Yearly": 12
	}
	if frequency not in mapping:
		frappe.throw(f"Häufigkeit '{frequency}' wurde nicht gefunden.")
	return mapping[frequency]

def process_auto_contract_invoices():
	# get all due contracts
	contracts = frappe.get_all(
		"Contract",
        filters={
			"next_invoice_date": ["<=", today()],
        	"status": "Active",
        	"enable_auto_invoicing": 1
        },
		or_filters=[
            ["end_date", ">=", today()],
            ["end_date", "is", "not set"]
        ],
        pluck="name"
    )
	
	for contract_name in contracts:
		try:
			create_contract_invoice(contract_name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title=f"Auto-Invoicing Failed for {contract_name}",
				message=frappe.get_traceback()
			)
	
	# deactivate expired contracts
	try:
		set_contracts_inactive()
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(
			title="Deactivate Contracts Failed",
			message=frappe.get_traceback()
		)

def create_contract_invoice(contract_name):
	contract_doc = frappe.get_doc("Contract", contract_name)
	
	sinv = frappe.get_doc({
		'doctype': 'Sales Invoice',
		'customer': contract_doc.customer,
		'taxes_and_charges': contract_doc.sales_taxes_and_charges_template,
		'payment_terms_template': contract_doc.payment_terms_template,
		'posting_date': today(),
		'company': frappe.defaults.get_user_default("Company")
	})
	
	for item in contract_doc.services:
		sinv.append('items', {
			'item_code': item.item,
			'qty': item.qty,
			'rate': item.rate,
			'description': item.description
        });
		
	sinv.set_missing_values()
	
	sinv.insert(ignore_permissions=True)

	# submit invoice if set in contract
	if contract_doc.auto_submit_invoices:
		sinv.submit()
	

	# add link to SINV to periods
	contract_doc.append('periods', {
		'start_date': contract_doc.last_execution_date or contract_doc.start_date,
		'end_date': contract_doc.next_invoice_date,
		'invoice': sinv.name,
		'invoice_date': sinv.posting_date,
		"invoice_status": sinv.status
	})

	# update contract
	contract_doc.last_execution_date = getdate()
	contract_doc.set_invoice_date_manually = 0
	contract_doc.next_invoice_date = get_next_date(contract_doc)

	contract_doc.save()

	return

def set_contracts_inactive():
	contracts_to_close = frappe.get_all(
		"Contract",
		filters={
			"end_date": ["<=", today()],
			"status": "Active",
			"enable_auto_invoicing": 1
		},
		pluck="name"
	)

	for contract_name in contracts_to_close:
		try:
			contract_doc = frappe.get_doc("Contract", contract_name)
			if not contract_doc.end_date:
				return

			flag_remaining_unbilled_period(contract_doc)

			contract_doc.status = "Inactive"
			contract_doc.flags.ignore_permission = True
			contract_doc.save()
		except Exception:
			frappe.log_error(
				title=f"Contract Deactivation Failed: {contract_name}",
				message=frappe.get_traceback()
			)
	return

def flag_remaining_unbilled_period(contract):
	last_billed = contract.last_execution_date or contract.start_date

	if not last_billed:
		return
		
	unbilled_days = date_diff(contract.end_date, last_billed)
	
	if unbilled_days > 0:
		contract.unbilled_days_remaining = unbilled_days
		contract.has_pending_final_period = 1

def sync_contract_status(doc, method):
	if not doc.name:
		return

	if doc.amended_from:
		relink_amended_invoice(doc)

	period_rows = frappe.get_all("Contract Period", filters={"invoice": doc.name}, fields=["parent", "name"])

	if not period_rows:
		return

	for row in period_rows:
		contract = frappe.get_doc("Contract", row.parent)
		for child in contract.periods:
			if child.name == row.name:
				child.invoice_status = doc.status
		contract.save(ignore_permissions=True)

