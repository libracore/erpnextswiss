# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and Contributors
# See license.txt
from __future__ import unicode_literals

from unittest.mock import MagicMock, patch

import frappe
import unittest

from erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection import (
	ebicsConnection,
	execute_payment,
)

class TestebicsConnection(unittest.TestCase):
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
