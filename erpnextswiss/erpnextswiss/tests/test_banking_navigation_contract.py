"""Keep the v16 banking navigation aligned with the actual EBICS data flow."""

import json
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
SIDEBAR = APP_ROOT / "workspace_sidebar" / "schweizer_buchhaltung.json"
WORKSPACES = APP_ROOT / "erpnextswiss" / "workspace"

BANK_LINKS = {
    "Kontoauszüge / EBICS-Abrufe": "EBICS Download",
    "Bankbewegungen": "Bank Transaction",
    "EBICS-Verbindungen": "ebics Connection",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestBankingNavigationContract(unittest.TestCase):
    def test_sidebar_reaches_current_bank_records(self):
        sidebar = load_json(SIDEBAR)
        links = {
            item["label"]: item["link_to"]
            for item in sidebar["items"]
            if item["type"] == "Link" and item["link_type"] == "DocType"
        }
        for label, target in BANK_LINKS.items():
            self.assertEqual(links[label], target)

    def test_payment_workspace_shortcuts_and_content_agree(self):
        workspace = load_json(WORKSPACES / "zahlungsverkehr" / "zahlungsverkehr.json")
        links = {item["label"]: item["link_to"] for item in workspace["links"]}
        shortcuts = {item["label"]: item["link_to"] for item in workspace["shortcuts"]}
        blocks = json.loads(workspace["content"])
        rendered_names = [
            block["data"]["shortcut_name"]
            for block in blocks if block["type"] == "shortcut"
        ]
        self.assertEqual(len(rendered_names), len(set(rendered_names)))
        self.assertEqual(set(rendered_names), set(shortcuts))
        for label, target in BANK_LINKS.items():
            self.assertEqual(links[label], target)
            self.assertEqual(shortcuts[label], target)
            self.assertIn(label, rendered_names)
        # The old statement DocType is still accessible as an archive, not
        # presented as the source of today's automated downloads.
        self.assertEqual(links["Ältere EBICS-Auszüge"], "ebics Statement")
        self.assertNotIn("EBICS-Auszüge", links)

    def test_landing_workspace_exposes_current_bank_records(self):
        workspace = load_json(WORKSPACES / "erpnextswiss" / "erpnextswiss.json")
        links = {item["label"]: item["link_to"] for item in workspace["links"]}
        shortcuts = {item["label"]: item["link_to"] for item in workspace["shortcuts"]}
        rendered_names = {
            block["data"]["shortcut_name"]
            for block in json.loads(workspace["content"])
            if block["type"] == "shortcut"
        }
        for label, target in BANK_LINKS.items():
            self.assertEqual(links[label], target)
            self.assertEqual(shortcuts[label], target)
            self.assertIn(label, rendered_names)

    def test_settings_workspace_reaches_connection_without_new_permissions(self):
        workspace = load_json(WORKSPACES / "schweiz_einstellungen" / "schweiz_einstellungen.json")
        self.assertEqual(
            next(item["link_to"] for item in workspace["shortcuts"]
                 if item["label"] == "EBICS-Verbindungen"),
            "ebics Connection",
        )
        roles = {item["role"] for item in workspace["roles"]}
        self.assertEqual(roles, {"System Manager", "Accounts Manager"})
        download = load_json(
            APP_ROOT / "erpnextswiss" / "doctype" / "ebics_download" / "ebics_download.json"
        )
        readers = {item["role"] for item in download["permissions"] if item.get("read")}
        self.assertEqual(readers, {"System Manager", "Accounts Manager"})

    def test_workspace_and_sidebar_are_reapplied_on_migration(self):
        hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
        setup = (APP_ROOT / "setup" / "install.py").read_text(encoding="utf-8")
        self.assertIn('after_migrate = "erpnextswiss.setup.install.after_migrate"', hooks)
        self.assertIn("ensure_workspace_records()", setup)
        self.assertIn("ensure_workspace_sidebar_records()", setup)


if __name__ == "__main__":
    unittest.main()
