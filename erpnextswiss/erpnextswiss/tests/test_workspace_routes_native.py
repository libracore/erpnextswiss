import json
import os
import unittest
from uuid import uuid4

import frappe

from erpnextswiss.setup.install import ensure_v16_desk_records
from erpnextswiss.setup.workspace_routes import (
    LEGACY_PAGE_ROLES, WORKSPACE_ROUTE_PAGES, retire_workspace_route_pages, retired_route_page_name,
)


class TestWorkspaceRoutesNative(unittest.TestCase):
    def setUp(self):
        self.user = frappe.session.user
        frappe.set_user("Administrator")
        self.savepoint = "routes_" + uuid4().hex
        frappe.db.savepoint(self.savepoint)
        self.addCleanup(self.rollback_test)

    def rollback_test(self):
        try:
            frappe.set_user("Administrator")
            frappe.db.rollback(save_point=self.savepoint)
        finally:
            frappe.set_user(self.user)

    def create_legacy_proxy(self, name, **overrides):
        # Reproduce the invalid duplicate routes imported by older standard JSONs.
        # Normal Page.save must not be allowed to create this state in v16.
        data = dict(doctype="Page", name=name, page_name=name, title=WORKSPACE_ROUTE_PAGES[name],
                    standard="Yes", module="ERPNextSwiss")
        data.update(overrides)
        page = frappe.get_doc(data)
        page.db_insert()
        for role in LEGACY_PAGE_ROLES:
            frappe.get_doc(doctype="Has Role", name=uuid4().hex, parent=name,
                          parenttype="Page", parentfield="roles", role=role).db_insert()
        return page

    def test_fresh_install_has_workspaces_without_page_collisions(self):
        for name, workspace in WORKSPACE_ROUTE_PAGES.items():
            self.assertFalse(frappe.db.exists("Page", name))
            self.assertTrue(frappe.db.exists("Workspace", workspace))
            # Native save invokes the route validator with normal flags.
            frappe.get_doc("Workspace", workspace).save()
        self.assertEqual(retire_workspace_route_pages(), [])

    def test_legacy_upgrade_archives_proxies_and_preserves_workspace_content(self):
        before = {name: frappe.get_doc("Workspace", name).content for name in set(WORKSPACE_ROUTE_PAGES.values())}
        for name in WORKSPACE_ROUTE_PAGES:
            self.create_legacy_proxy(name)
        legacy = "erpnextswiss"
        version = frappe.get_doc(doctype="Version", name=uuid4().hex, ref_doctype="Page",
                                 docname=legacy, data=json.dumps({"changed": [["title", "Old", "New"]]}))
        version.db_insert()
        comment = frappe.get_doc("Page", legacy).add_comment("Comment", "Preserve this history")
        custom_role = frappe.get_doc(doctype="Custom Role", page=legacy,
                                     roles=[{"role": "HR User"}]).insert()
        extra_role = frappe.get_doc(doctype="Has Role", name=uuid4().hex, parent=legacy,
            parenttype="Page", parentfield="roles", role="HR Manager")
        extra_role.db_insert()
        file = frappe.get_doc(doctype="File", name=uuid4().hex, file_name="reference.txt",
            file_url="/private/files/synthetic-reference.txt", is_private=1,
            attached_to_doctype="Page", attached_to_name=legacy)
        file.db_insert()
        self.assertEqual(set(retire_workspace_route_pages()), set(WORKSPACE_ROUTE_PAGES))
        for name in WORKSPACE_ROUTE_PAGES:
            self.assertFalse(frappe.db.exists("Page", name))
            archived = frappe.get_doc("Page", retired_route_page_name(name))
            self.assertEqual(archived.title, WORKSPACE_ROUTE_PAGES[name])
            archived.load_assets()
            self.assertIn(retired_route_page_name(name), archived.script)
        self.assertEqual(frappe.db.get_value("Version", version.name, "docname"), retired_route_page_name(legacy))
        self.assertEqual(frappe.db.get_value("Comment", comment.name, "reference_name"), retired_route_page_name(legacy))
        self.assertEqual(frappe.db.get_value("Custom Role", custom_role.name, "page"), retired_route_page_name(legacy))
        self.assertEqual(frappe.db.get_value("File", file.name, "attached_to_name"), retired_route_page_name(legacy))
        self.assertEqual(frappe.db.get_value("Has Role", extra_role.name, "parent"), retired_route_page_name(legacy))
        ensure_v16_desk_records()
        ensure_v16_desk_records()
        self.assertEqual(before, {name: frappe.get_doc("Workspace", name).content for name in before})
        self.assertEqual(retire_workspace_route_pages(), [])

    def test_modified_last_proxy_blocks_the_entire_retirement(self):
        for name in WORKSPACE_ROUTE_PAGES:
            self.create_legacy_proxy(name, title="Custom page" if name == "schweiz-einstellungen" else WORKSPACE_ROUTE_PAGES[name])
        with self.assertRaises(frappe.ValidationError):
            retire_workspace_route_pages()
        self.assertTrue(all(frappe.db.exists("Page", name) for name in WORKSPACE_ROUTE_PAGES))

    def test_guest_cannot_run_retirement(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            retire_workspace_route_pages()


def prepare_browser_site():
    """Prepare only the disposable GitHub CI site, never an installed customer site."""
    if (frappe.local.site != "test_site" or not frappe.conf.allow_tests
            or os.environ.get("GITHUB_ACTIONS") != "true"):
        raise RuntimeError("Browser fixtures are restricted to the disposable GitHub test_site")
    frappe.set_user("Administrator")
    for app in ("frappe", "erpnext"):
        frappe.db.set_value("Installed Application", {"app_name": app}, "is_setup_complete", 1)
    frappe.db.set_single_value("System Settings", "setup_complete", 1)
    frappe.db.set_single_value("System Settings", "enable_onboarding", 0)
    fixture = TestWorkspaceRoutesNative()
    for name in WORKSPACE_ROUTE_PAGES:
        if not frappe.db.exists("Page", retired_route_page_name(name)):
            fixture.create_legacy_proxy(name)
    retire_workspace_route_pages()
    frappe.db.commit()
    frappe.clear_cache()
    return {"site": "test_site", "retained_pages": len(WORKSPACE_ROUTE_PAGES)}
