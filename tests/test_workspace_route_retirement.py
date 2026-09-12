import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch


class Proxy(dict):
    def __getattr__(self, key):
        return self[key]


class WorkspaceRouteRetirementTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.pages = {}
        self.role = "System Manager"

        def exists(doctype, name):
            if doctype == "Page":
                return name in self.pages
            return False

        def only_for(role):
            if self.role != role:
                raise PermissionError("restricted migration")

        def fail(message, error):
            raise error(message)

        fake = SimpleNamespace(
            db=SimpleNamespace(exists=exists, get_value=lambda *a, **k: self.events.append(("lock", a, k))),
            get_doc=lambda dt, name: self.pages[name], only_for=only_for, _=lambda value: value,
            throw=fail, ValidationError=ValueError,
            rename_doc=lambda dt, name, target, **kwargs: self.events.append(("rename", name, target, kwargs)),
        )
        patcher = patch.dict(sys.modules, {
            "frappe": fake,
            "frappe.model.rename_doc": SimpleNamespace(rename_doc=fake.rename_doc),
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        spec = importlib.util.spec_from_file_location("workspace_routes_under_test",
            Path(__file__).resolve().parents[1] / "erpnextswiss" / "setup" / "workspace_routes.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        for name, title in self.module.WORKSPACE_ROUTE_PAGES.items():
            self.pages[name] = Proxy(name=name, page_name=name, title=title,
                module="ERPNextSwiss", standard="Yes",
                roles=[SimpleNamespace(role=role) for role in self.module.LEGACY_PAGE_ROLES])

    def test_rename_only_after_all_preflights_and_without_merge_or_commit(self):
        self.assertEqual(self.module.retire_workspace_route_pages(), list(self.pages))
        self.assertEqual(self.events[-6:], [
            ("rename", name, "kt-swiss-route-" + name, {"force": True, "ignore_permissions": True,
             "show_alert": False, "rebuild_search": False}) for name in self.pages
        ])
        self.assertEqual(len([event for event in self.events if event[0] == "lock"]), 6)

    def test_customized_late_page_prevents_entire_batch(self):
        for field, value in (("module", "Another App"), ("standard", "No"), ("title", "Custom title"),
                             ("system_page", 1), ("restrict_to_domain", "Custom")):
            page = self.pages["schweiz-einstellungen"]
            with self.subTest(field=field), patch.dict(page, {field: value}):
                with self.assertRaises(ValueError):
                    self.module.retire_workspace_route_pages()
                self.assertFalse(any(event[0] == "rename" for event in self.events))

    def test_additional_roles_are_preserved_for_native_rename(self):
        page = self.pages["erpnextswiss"]
        page.roles.append(SimpleNamespace(role="HR User"))
        self.module.retire_workspace_route_pages()
        self.assertIn("HR User", {row.role for row in page.roles})

    def test_occupied_target_prevents_entire_batch_without_merge(self):
        self.pages["kt-swiss-route-schweiz-einstellungen"] = Proxy(name="foreign")
        with self.assertRaises(ValueError):
            self.module.retire_workspace_route_pages()
        self.assertFalse(any(event[0] == "rename" for event in self.events))

    def test_empty_install_is_noop_and_other_users_are_denied(self):
        self.pages.clear()
        self.assertEqual(self.module.retire_workspace_route_pages(), [])
        self.assertEqual(self.events, [])
        self.role = "Accounts User"
        with self.assertRaises(PermissionError):
            self.module.retire_workspace_route_pages()

    def test_obsolete_proxies_cannot_be_reimported_by_sync(self):
        root = Path(__file__).resolve().parents[1] / "erpnextswiss" / "erpnextswiss" / "page"
        for name in self.module.WORKSPACE_ROUTE_PAGES:
            slug = name.replace("-", "_")
            self.assertFalse((root / slug / (slug + ".json")).exists())
