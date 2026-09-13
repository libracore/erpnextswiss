import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "erpnextswiss"


class FixtureExportTests(unittest.TestCase):
    def test_split_preserves_every_existing_field_definition(self):
        fields = []
        for file in (ROOT / "fixtures").glob("*.json"):
            fields.extend(json.loads(file.read_text(encoding="utf-8")))
        canonical = json.dumps(sorted(fields, key=lambda row: row["name"]),
                               sort_keys=True, separators=(",", ":"))
        self.assertEqual(len(fields), 41)
        # Semantic snapshot of all 41 definitions in 4640331, before grouping.
        self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(),
                         "81004c98b9a0b66d3d1ade0402ac6bb538d3594f62b7e3d179993c89c082f2ba")

    def test_native_export_filters_match_exact_files_and_isolate_optional_targets(self):
        tree = ast.parse((ROOT / "hooks.py").read_text(encoding="utf-8"))
        config = next(ast.literal_eval(node.value) for node in tree.body
                      if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "fixtures" for target in node.targets))
        exported = set()
        files = set()
        for entry in config:
            self.assertEqual(entry["dt"], "Custom Field")
            self.assertEqual(set(entry), {"dt", "filters"} | ({"prefix"} if entry.get("prefix") else set()))
            self.assertEqual(len(entry["filters"]), 1)
            self.assertEqual(entry["filters"][0][:2], ["name", "in"])
            names = entry["filters"][0][2]
            self.assertEqual(len(names), len(set(names)))
            self.assertFalse(exported.intersection(names))
            exported.update(names)
            filename = (entry["prefix"] + "_" if entry.get("prefix") else "") + "custom_field.json"
            files.add(filename)
            rows = json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))
            self.assertEqual(set(names), {row["name"] for row in rows})
            if filename == "hr_custom_field.json":
                self.assertEqual({row["dt"] for row in rows}, {"Expense Claim"})
            else:
                self.assertNotIn("Expense Claim", {row["dt"] for row in rows})
        self.assertEqual(files, {file.name for file in (ROOT / "fixtures").glob("*.json")})
        self.assertEqual(len(exported), 41)
