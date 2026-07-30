# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import Mock, patch

from erpnextswiss.erpnextswiss import caldav


class TestCalDavFeed(unittest.TestCase):
    def test_secret_comparison_is_exact(self):
        self.assertTrue(caldav._secret_matches("correct", "correct"))
        self.assertFalse(caldav._secret_matches("wrong", "correct"))
        self.assertFalse(caldav._secret_matches("", "correct"))
        self.assertFalse(caldav._secret_matches("correct", ""))

    @patch.object(caldav, "today", return_value="2026-07-29")
    @patch.object(caldav.frappe, "get_all", return_value=[])
    @patch.object(caldav.frappe.db, "exists", return_value=True)
    @patch.object(caldav.frappe, "get_doc")
    def test_todo_feed_uses_parameterized_frappe_query(
        self,
        get_doc,
        _exists,
        get_all,
        _today,
    ):
        settings = Mock()
        settings.get.return_value = "todo-secret"
        settings.todo_feed_enabled = 1
        get_doc.return_value = settings

        calendar = caldav.get_todo_feed_content("todo-secret", "user@example.com")

        self.assertIsNotNone(calendar)
        get_all.assert_called_once_with(
            "ToDo",
            filters={
                "date": [">=", "2026-07-29"],
                "owner": "user@example.com",
                "status": "Open",
            },
            fields=["name", "description", "creation", "modified"],
        )

    @patch.object(caldav, "today", return_value="2026-07-29")
    @patch.object(caldav.frappe, "get_all", return_value=[])
    @patch.object(caldav.frappe, "get_meta")
    @patch.object(caldav.frappe, "get_doc")
    def test_crm_feed_rejects_unexpected_doctype(
        self,
        get_doc,
        get_meta,
        get_all,
        _today,
    ):
        settings = Mock()
        settings.get.return_value = "crm-secret"
        settings.crm_feed_enabled = 1
        settings.crm_source = "User"
        settings.crm_source_field = "modified"
        get_doc.return_value = settings

        self.assertIsNone(caldav.get_crm_feed_content("crm-secret"))
        get_meta.assert_not_called()
        get_all.assert_not_called()

    @patch.object(caldav, "today", return_value="2026-07-29")
    @patch.object(caldav.frappe, "get_all", return_value=[])
    @patch.object(caldav.frappe, "get_meta")
    @patch.object(caldav.frappe, "get_doc")
    def test_crm_feed_fetches_only_required_customer_fields(
        self,
        get_doc,
        get_meta,
        get_all,
        _today,
    ):
        settings = Mock()
        settings.get.return_value = "crm-secret"
        settings.crm_feed_enabled = 1
        settings.crm_source = "Customer"
        settings.crm_source_field = "modified"
        get_doc.return_value = settings
        get_meta.return_value.has_field.return_value = True

        calendar = caldav.get_crm_feed_content("crm-secret")

        self.assertIsNotNone(calendar)
        get_all.assert_called_once_with(
            "Customer",
            filters=[["modified", ">=", "2026-07-29"]],
            fields=[
                "name",
                "modified",
                "owner",
                "email_id",
                "customer_name",
                "account_manager",
            ],
        )
