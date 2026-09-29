# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and Contributors
# See license.txt
from __future__ import unicode_literals

from unittest.mock import MagicMock, patch
from datetime import date, datetime

import frappe
import unittest

from erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection import (
	ebicsConnection,
	execute_payment,
	_has_transport_permission,
)


def htd_fixture(levels=("T",), account="CH8600761649749632002", signatures=2):
	permissions = "".join(
		'<Permission AuthorisationLevel="{0}"><AdminOrderType>BTU</AdminOrderType>'
		'<Service><ServiceName>MCT</ServiceName><Scope>CH</Scope>'
		'<MsgName version="09">pain.001</MsgName></Service><AccountID>ID0001</AccountID>'
		'</Permission>'.format(level) for level in levels
	)
	return (
		'<HTDResponseOrderData xmlns="urn:org:ebics:H005">'
		'<PartnerInfo><AccountInfo ID="ID0001"><AccountNumber international="true">{0}</AccountNumber>'
		'</AccountInfo><OrderInfo><AdminOrderType>BTU</AdminOrderType><Service>'
		'<ServiceName>MCT</ServiceName><Scope>CH</Scope><MsgName version="09">pain.001</MsgName>'
		'</Service><NumSigRequired>{2}</NumSigRequired></OrderInfo></PartnerInfo>'
		'<UserInfo>{1}</UserInfo></HTDResponseOrderData>'
	).format(account, permissions, signatures).encode()


PAYMENT_BTF = {'service': 'MCT', 'msg_name': 'pain.001', 'scope': 'CH', 'version': '09'}

class TestebicsConnection(unittest.TestCase):
	def test_veu_permission_requires_only_t_for_exact_account_and_format(self):
		self.assertTrue(_has_transport_permission(htd_fixture(),
			"CH8600761649749632002", PAYMENT_BTF, min_signatures=2))
		for levels, iban, btf in (
			(("E",), "CH8600761649749632002", PAYMENT_BTF),
			(("T", "E"), "CH8600761649749632002", PAYMENT_BTF),
			(("T",), "CH5900761649749632003", PAYMENT_BTF),
			(("T",), "CH8600761649749632002", {**PAYMENT_BTF, 'version': '03'}),
		):
			with self.subTest(levels=levels, iban=iban, btf=btf):
				self.assertFalse(_has_transport_permission(htd_fixture(levels), iban, btf,
					min_signatures=2))
		self.assertFalse(_has_transport_permission(htd_fixture(signatures=1),
			"CH8600761649749632002", PAYMENT_BTF, min_signatures=2))

	@patch("erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.BusinessTransactionFormat")
	def test_veu_blocks_e_signature_before_upload(self, btf):
		connection = ebicsConnection({
			'doctype': 'ebics Connection', 'name': 'AKB', 'company': 'KT',
			'scope': 'CH', 'payment_btf_version': '09', 'require_veu': 1,
			'veu_signatures_required': 2,
		})
		connection.check_permission = MagicMock()
		client = MagicMock()
		client.HTD.return_value = htd_fixture(('E',))
		connection.get_client = MagicMock(return_value=client)
		payment = MagicMock(name='PAY-0001', docstatus=1, company='KT',
			pay_from_account='BANK')
		payment.name = 'PAY-0001'
		payment.create_bank_file.return_value = {'content': '<Document />', 'message_id': 'MSG-1'}
		account = MagicMock(iban='CH8600761649749632002', company='KT')
		with patch.object(frappe, 'get_doc', side_effect=[payment, account]):
			with self.assertRaises(Exception):
				connection.execute_payment('PAY-0001')
		client.BTU.assert_not_called()

	@patch("erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.BusinessTransactionFormat")
	def test_veu_submits_once_and_records_approval_state(self, btf):
		connection = ebicsConnection({
			'doctype': 'ebics Connection', 'name': 'AKB', 'company': 'KT',
			'scope': 'CH', 'payment_btf_version': '09', 'require_veu': 1,
			'veu_signatures_required': 2,
		})
		connection.check_permission = MagicMock()
		client = MagicMock()
		client.HTD.return_value = htd_fixture()
		client.BTU.return_value = 'AAAD'
		connection.get_client = MagicMock(return_value=client)
		payment = MagicMock(docstatus=1, company='KT', pay_from_account='BANK')
		payment.name = 'PAY-0001'
		payment.create_bank_file.return_value = {'content': '<Document />', 'message_id': 'MSG-1'}
		account = MagicMock(iban='CH8600761649749632002', company='KT')
		with patch.object(frappe, 'get_doc', side_effect=[payment, account]), \
			patch.object(frappe.db, 'sql', return_value=[('',)]) as sql, \
			patch.object(frappe.db, 'set_value') as set_value, \
			patch.object(frappe.db, 'commit') as commit:
			result = connection.execute_payment('PAY-0001')
		self.assertEqual(result['status'], 'awaiting_bank_veu')
		self.assertEqual(result['order_id'], 'AAAD')
		client.BTU.assert_called_once_with(btf.return_value, '<Document />')
		self.assertEqual(set_value.call_args_list[0].args[2]['ebics_transfer_status'], 'Sending')
		self.assertEqual(set_value.call_args_list[1].args[2]['ebics_transfer_status'], 'Awaiting bank VEU')
		self.assertEqual(commit.call_count, 2)

	@patch("erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.BusinessTransactionFormat")
	def test_veu_never_resends_a_recorded_attempt(self, btf):
		connection = ebicsConnection({
			'doctype': 'ebics Connection', 'name': 'AKB', 'company': 'KT',
			'scope': 'CH', 'payment_btf_version': '09', 'require_veu': 1,
			'veu_signatures_required': 2,
		})
		connection.check_permission = MagicMock()
		client = MagicMock()
		client.HTD.return_value = htd_fixture()
		connection.get_client = MagicMock(return_value=client)
		payment = MagicMock(docstatus=1, company='KT', pay_from_account='BANK')
		payment.name = 'PAY-0001'
		payment.create_bank_file.return_value = {'content': '<Document />', 'message_id': 'MSG-2'}
		account = MagicMock(iban='CH8600761649749632002', company='KT')
		with patch.object(frappe, 'get_doc', side_effect=[payment, account]), \
			patch.object(frappe.db, 'sql', return_value=[('Awaiting bank outcome (pre-VEU)',)]), \
			patch.object(frappe.db, 'set_value') as set_value:
			with self.assertRaises(Exception):
				connection.execute_payment('PAY-0001')
		client.BTU.assert_not_called()
		set_value.assert_not_called()

	def test_synced_until_accepts_database_date_and_normalizes_input(self):
		for supplied in (date(2026, 9, 28), datetime(2026, 9, 28, 12, 30), "2026-09-28"):
			with self.subTest(supplied=supplied):
				connection = ebicsConnection({"doctype": "ebics Connection", "synced_until": supplied})
				connection.before_save()
				self.assertEqual(connection.synced_until, date(2026, 9, 28))

	@patch("erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.frappe.utils.get_site_path")
	def test_keys_file_uses_absolute_site_path_without_prefixing_it_again(self, get_site_path):
		get_site_path.return_value = "/home/frappe/frappe-bench/sites/erp.local"
		connection = ebicsConnection({
			"doctype": "ebics Connection",
			"name": "AKB CantoConnect 1773",
		})

		self.assertEqual(
			connection.get_keys_file_name(),
			"/home/frappe/frappe-bench/sites/erp.local/AKB_CantoConnect_1773.keys",
		)

	@patch("erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.BusinessTransactionFormat")
	def test_execute_payment_uses_btu_with_configured_btf_version(self, btf):
		connection = ebicsConnection({
			"doctype": "ebics Connection",
			"name": "AKB",
			"scope": "CH",
			"payment_btf_version": "09",
		})
		connection.check_permission = MagicMock()
		connection.get_client = MagicMock()
		payment = MagicMock()
		payment.create_bank_file.return_value = {"content": "<Document />"}

		with patch.object(frappe, "get_doc", return_value=payment):
			connection.execute_payment("PAY-0001")

		btf.assert_called_once_with(
			service="MCT",
			msg_name="pain.001",
			scope="CH",
			version="09",
		)
		connection.get_client.return_value.BTU.assert_called_once_with(
			btf.return_value,
			"<Document />",
		)
		connection.get_client.return_value.BTD.assert_not_called()

	@patch("erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.frappe.get_doc")
	def test_whitelisted_execute_payment_loads_connection(self, get_doc):
		connection = MagicMock()
		get_doc.return_value = connection

		execute_payment("AKB", "PAY-0001")

		get_doc.assert_called_once_with("ebics Connection", "AKB")
		connection.check_permission.assert_called_once_with("write")
		connection.execute_payment.assert_called_once_with("PAY-0001")
