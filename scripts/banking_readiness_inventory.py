"""Read-only bank integration inventory. Never initializes a client or reads secrets."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import subprocess


DOCTYPES = (
    "Bank Account", "Bank Transaction", "Bank Statement Import", "Bank Transaction Rule",
    "Payment Entry", "Payment Proposal", "Journal Entry", "ebics Connection", "ebics Statement",
)
SOURCE_FILES = (
    "hooks.py", "erpnextswiss/ebics.py",
    "erpnextswiss/doctype/ebics_connection/ebics_connection.py",
    "erpnextswiss/doctype/ebics_statement/ebics_statement.py",
    "erpnextswiss/page/bank_wizard/bank_wizard.py",
    "erpnextswiss/page/bankimport/bankimport.py",
    "erpnextswiss/page/match_payments/match_payments.py",
    "erpnextswiss/doctype/payment_proposal/payment_proposal.py",
)


def account_summary(accounts, ledgers):
    """Report mapping defects without emitting account names, IBANs or party details."""
    mapped = {row["name"]: row for row in ledgers}
    counts = Counter(total=len(accounts))
    currencies = Counter()
    identities = Counter()
    for bank in accounts:
        if bank.get("disabled"):
            counts["disabled"] += 1
            continue
        counts["active"] += 1
        iban = "".join((bank.get("iban") or "").split()).upper()
        if iban:
            identities[(bank.get("company"), iban)] += 1
        else:
            counts["missing_iban"] += 1
        ledger = mapped.get(bank.get("account"))
        if not ledger:
            counts["missing_ledger"] += 1
            continue
        if ledger.get("company") != bank.get("company"):
            counts["company_mismatch"] += 1
        if ledger.get("account_type") != "Bank" or ledger.get("is_group") or ledger.get("disabled"):
            counts["invalid_bank_ledger"] += 1
        currencies[ledger.get("account_currency") or "UNSPECIFIED"] += 1
    counts["duplicate_active_company_iban_groups"] = sum(value > 1 for value in identities.values())
    return {"counts": dict(sorted(counts.items())), "ledger_currencies": dict(sorted(currencies.items()))}


def banking_scheduler(value):
    """Keep only matching methods, including nested cron schedules."""
    if isinstance(value, dict):
        return {key: selected for key, child in value.items() if (selected := banking_scheduler(child))}
    if isinstance(value, (list, tuple)):
        return [method for method in value if isinstance(method, str)
                and any(term in method.lower() for term in ("bank", "ebics", "payment"))]
    return None


def inventory(frappe):
    apps = {}
    for app in frappe.get_installed_apps():
        directory = Path(frappe.get_app_path(app)).parent
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory, capture_output=True, text=True, timeout=10)
        try:
            version = metadata.version(app)
        except metadata.PackageNotFoundError:
            version = None
        apps[app] = {"version": version, "commit": revision.stdout.strip() if revision.returncode == 0 else None}
    swiss = Path(frappe.get_app_path("erpnextswiss"))
    sources = {name: hashlib.sha256((swiss / name).read_bytes()).hexdigest() for name in SOURCE_FILES}
    doctypes = {}
    for doctype in DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            doctypes[doctype] = {"installed": False}
            continue
        meta = frappe.get_meta(doctype)
        doctypes[doctype] = {"installed": True, "count": frappe.db.count(doctype),
            "permissions": [{key: row.get(key) for key in ("role", "permlevel", "read", "write", "create", "submit", "cancel", "export")}
                            for row in meta.permissions],
            "user_permission_count": frappe.db.count("User Permission", {"allow": doctype})}
    events = frappe.get_hooks("doc_events")
    hooks = {"doc_events": {name: events.get(name) for name in (*DOCTYPES, "*") if events.get(name)}}
    for kind in ("override_doctype_class", "extend_doctype_class", "has_permission", "permission_query_conditions"):
        configured = frappe.get_hooks(kind)
        hooks[kind] = {name: configured.get(name) for name in DOCTYPES if configured.get(name)}
    scheduler = frappe.get_hooks("scheduler_events")
    hooks["banking_scheduler"] = banking_scheduler(scheduler)
    scripts = []
    if frappe.db.exists("DocType", "Server Script"):
        for row in frappe.get_all("Server Script", filters={"disabled": 0},
                                  fields=["script_type", "reference_doctype", "doctype_event", "script"]):
            if row.reference_doctype in DOCTYPES or any(term in (row.script or "").lower() for term in ("bank", "ebics", "payment")):
                scripts.append({"type": row.script_type, "doctype": row.reference_doctype, "event": row.doctype_event,
                                "source_hash": hashlib.sha256((row.script or "").encode()).hexdigest()})
    accounts = frappe.get_all("Bank Account", filters={"is_company_account": 1},
                               fields=["name", "company", "account", "iban", "disabled"])
    ledgers = frappe.get_all("Account", filters={"name": ["in", [row.account for row in accounts if row.account]]},
                              fields=["name", "company", "account_type", "account_currency", "disabled", "is_group"]) if accounts else []
    connections = frappe.get_all("ebics Connection", fields=["enable_sync", "activated", "ebics_version"])
    return {"schema": "kt.bank-readiness.v1", "checked_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True, "bank_calls": 0, "apps": apps, "swiss_source_sha256": sources,
        "doctypes": doctypes, "hooks": hooks, "relevant_server_scripts": scripts,
        "company_accounts": account_summary(accounts, ledgers),
        "connections": {"total": len(connections), "sync_enabled": sum(bool(row.enable_sync) for row in connections),
                        "activated": sum(bool(row.activated) for row in connections),
                        "versions": dict(Counter(row.ebics_version for row in connections))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--sites-path", required=True)
    args = parser.parse_args()
    import frappe

    frappe.init(site=args.site, sites_path=args.sites_path)
    frappe.connect()
    try:
        # Database-enforced read-only transaction: a surprising hook cannot commit business writes.
        frappe.db.sql("START TRANSACTION READ ONLY")
        frappe.set_user("Administrator")
        print(json.dumps(inventory(frappe), sort_keys=True, indent=2, default=str))
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
