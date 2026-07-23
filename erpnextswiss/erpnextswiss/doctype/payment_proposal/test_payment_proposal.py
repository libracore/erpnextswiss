# -*- coding: utf-8 -*-
# Copyright (c) 2018, libracore (https://www.libracore.com) and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from datetime import datetime, timezone

from erpnextswiss.erpnextswiss.iso20022 import (
	create_message_id,
	create_payment_file_name,
	is_qr_iban,
	is_valid_qr_reference,
)

class TestPaymentProposal(unittest.TestCase):
	def test_message_id_is_unique_and_swift_safe(self):
		first = create_message_id()
		second = create_message_id()

		self.assertNotEqual(first, second)
		self.assertRegex(first, r"^MSG-[0-9]{20}-[0-9A-F]{8}$")
		self.assertLessEqual(len(first), 35)

	def test_message_id_and_file_name_are_reproducible(self):
		message_id = create_message_id(
			now=datetime(2026, 7, 23, 7, 1, 15, 123456, tzinfo=timezone.utc),
			entropy="a1b2c3d4",
		)

		self.assertEqual(message_id, "MSG-20260723070115123456-A1B2C3D4")
		self.assertEqual(
			create_payment_file_name(message_id),
			"payments_MSG-20260723070115123456-A1B2C3D4.xml",
		)

	def test_qr_iban_detection(self):
		self.assertTrue(is_qr_iban("CH98 3000 5248 2100 1701 C"))
		self.assertFalse(is_qr_iban("CH86 0076 1649 7496 3200 2"))
		self.assertFalse(is_qr_iban("DE89370400440532013000"))

	def test_qr_reference_validation(self):
		self.assertTrue(is_valid_qr_reference("00 17010 00000 00000 00012 02132"))
		self.assertFalse(is_valid_qr_reference("001701000000000000001202131"))
		self.assertFalse(is_valid_qr_reference("120213"))
