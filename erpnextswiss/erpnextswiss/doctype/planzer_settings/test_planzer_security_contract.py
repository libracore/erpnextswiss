import json
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APP_ROOT.parents[1]


class TestPlanzerSecurityContract(unittest.TestCase):
    def test_sftp_requires_a_pinned_host_key(self):
        source = (APP_ROOT / "planzer.py").read_text(encoding="utf-8")

        self.assertIn("paramiko.RejectPolicy()", source)
        self.assertIn("HostKeyEntry.from_line", source)
        self.assertIn('settings.get("ssh_host_key")', source)
        self.assertNotIn("pysftp", source)
        self.assertNotIn("hostkeys = None", source)

    def test_planzer_settings_require_host_key_when_enabled(self):
        definition_path = (
            APP_ROOT
            / "doctype"
            / "planzer_settings"
            / "planzer_settings.json"
        )
        definition = json.loads(definition_path.read_text(encoding="utf-8"))
        fields = {field["fieldname"]: field for field in definition["fields"]}

        self.assertEqual(fields["port"].get("default"), "22")
        self.assertEqual(
            fields["ssh_host_key"].get("mandatory_depends_on"),
            "eval:doc.enabled",
        )

    def test_obsolete_pysftp_dependency_is_removed(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertNotIn('"pysftp"', pyproject)
        self.assertIn('"paramiko<4"', pyproject)


if __name__ == "__main__":
    unittest.main()
