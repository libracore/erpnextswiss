"""Inspect candidate Swiss field definitions without exposing values or changing data."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


RECORD_METADATA = {"doctype", "name", "creation", "modified", "owner", "modified_by", "idx", "docstatus"}
OPTIONAL_TARGETS = {"Expense Claim"}


def normalized(value):
    return None if value is None or value == "" else value


def inspect(frappe, directory):
    fields = []
    sources = {}
    for file in sorted(Path(directory).glob("*.json")):
        sources[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
        fields.extend(json.loads(file.read_text(encoding="utf-8")))
    if not fields or any(row.get("doctype") != "Custom Field" for row in fields):
        raise ValueError("Nonempty candidate Custom Field fixtures required")
    if len({row["name"] for row in fields}) != len(fields):
        raise ValueError("Duplicate candidate Custom Field identity")
    missing = []
    missing_targets = set()
    optional = []
    drift = []
    unsupported = set()
    metadata = frappe.get_meta("Custom Field")
    checked = 0
    for expected in fields:
        name, target = expected["name"], expected["dt"]
        if not frappe.db.exists("DocType", target):
            if target in OPTIONAL_TARGETS:
                optional.append(name)
            else:
                missing_targets.add(target)
            continue
        checked += 1
        if not frappe.db.exists("Custom Field", name):
            missing.append(name)
            continue
        actual = frappe.get_doc("Custom Field", name)
        attributes = set(expected) - RECORD_METADATA
        unsupported.update(field for field in attributes if not metadata.has_field(field))
        changed = [field for field in sorted(attributes) if metadata.has_field(field)
                   if normalized(actual.get(field)) != normalized(expected.get(field))]
        if changed:
            # Defaults/options can contain private values. Report attribute names only.
            drift.append({"name": name, "attributes": changed})
    return {"schema": "kt.swiss-fixture-inventory.v1", "checked_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True, "bank_calls": 0, "source_sha256": sources,
        "candidate_fields": len(fields), "applicable_fields": checked,
        "missing_custom_fields": sorted(missing), "missing_required_doctypes": sorted(missing_targets),
        "optional_target_absent": sorted(optional), "definition_drift": sorted(drift, key=lambda row: row["name"]),
        "unsupported_source_attributes": sorted(unsupported),
        "requires_review": bool(missing or missing_targets or drift)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--sites-path", required=True)
    parser.add_argument("--fixtures-dir", required=True)
    args = parser.parse_args(argv)
    import frappe

    frappe.init(site=args.site, sites_path=args.sites_path)
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        frappe.set_user("Administrator")
        print(json.dumps(inspect(frappe, args.fixtures_dir), sort_keys=True, indent=2))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
