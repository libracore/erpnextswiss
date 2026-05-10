# -*- coding: utf-8 -*-
# License: AGPL v3. See LICENCE

import json
import re
from pathlib import Path

import frappe


WORKSPACE_ROUTES = {
    "Schweizer Buchhaltung": "schweizer-buchhaltung",
    "Zahlungsverkehr": "zahlungsverkehr",
    "QR-Rechnung & E-Rechnung": "qr-rechnung-e-rechnung",
    "Schweizer MwSt": "schweizer-mwst",
    "Schweiz-Einstellungen": "schweiz-einstellungen",
}

BANKIMPORT_BANKS = [
    {'doctype': 'BankImport Bank','bank_name': 'UBS','legacy_ref': 'ubs','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'ZKB','legacy_ref': 'zkb','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'Raiffeisen','legacy_ref': 'raiffeisen','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'CreditSwiss','legacy_ref': 'cs','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'Migrosbank','legacy_ref': 'migrosbank','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'Postfinance','legacy_ref': 'postfinance','file_format': 'CAMT.054 Transaction Notification(camt054)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'Kreissparkasse','legacy_ref': 'ksk','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'Volksbank','legacy_ref': 'voba','file_format': 'CSV(csv)','bank_enabled': 1},
    {'doctype': 'BankImport Bank','bank_name': 'Aargauische Kantonalbank','legacy_ref': 'akb','file_format': 'CAMT.053 Bank Statement(camt053)','bank_enabled': 1},
]


def after_install():
    ensure_bankimport_banks()
    ensure_v16_desk_records()
    frappe.db.commit()


def after_migrate():
    ensure_bankimport_banks()
    ensure_v16_desk_records()
    frappe.db.commit()
    

def ensure_bankimport_banks():
    if not frappe.db.exists("DocType", "ERPNextSwiss Settings"):
        return

    doc = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
    changed = False
    existing_by_name = {row.bank_name: row for row in doc.get("bankimport_table") or []}
    existing_by_ref = {row.legacy_ref: row for row in doc.get("bankimport_table") or [] if row.legacy_ref}

    for bank in BANKIMPORT_BANKS:
        row = existing_by_name.get(bank["bank_name"]) or existing_by_ref.get(bank["legacy_ref"])
        if row:
            for fieldname in ("bank_name", "legacy_ref", "file_format", "bank_enabled"):
                if getattr(row, fieldname, None) != bank[fieldname]:
                    setattr(row, fieldname, bank[fieldname])
                    changed = True
            continue

        doc.append("bankimport_table", bank)
        changed = True

    if changed:
        doc.save(ignore_permissions=True)


def install_basic_docs():
    ensure_bankimport_banks()


def ensure_v16_desk_records():
    ensure_workspace_records()
    ensure_workspace_sidebar_records()
    ensure_desktop_icon_records()
    _clear_desk_navigation_cache()


def ensure_workspace_records():
    workspace_root = Path(frappe.get_app_path("erpnextswiss", "erpnextswiss", "workspace"))
    if not workspace_root.exists():
        return

    for workspace_file in workspace_root.glob("*/*.json"):
        data = json.loads(workspace_file.read_text(encoding="utf-8"))
        if data.get("doctype") != "Workspace" or not data.get("name"):
            continue
        _upsert_workspace_record(_prepare_workspace_data(data))


def _prepare_workspace_data(data):
    data = data.copy()
    for meta_field in ("creation", "modified", "modified_by", "owner"):
        data.pop(meta_field, None)
    data.setdefault("type", "Workspace")
    data.setdefault("public", 1)
    data.setdefault("for_user", "")
    data["app"] = "erpnextswiss"
    if frappe.get_meta("Workspace").has_field("route"):
        data["route"] = data.get("route") or _workspace_route(data.get("name") or data.get("title") or data.get("label"))
    _sanitize_workspace_links(data)
    _sanitize_workspace_shortcuts(data)
    return data


def _upsert_workspace_record(data):
    existing_workspace = frappe.db.exists("Workspace", data["name"])
    if existing_workspace:
        workspace = frappe.get_doc("Workspace", existing_workspace)
        _clear_workspace_child_tables(workspace)
        workspace.update(data)
        _sanitize_workspace_links(workspace)
        _sanitize_workspace_shortcuts(workspace)
        workspace.save(ignore_permissions=True)
        return

    try:
        frappe.get_doc(data).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        frappe.clear_last_message()
        duplicate_workspace = (
            frappe.db.exists("Workspace", data["name"])
            or frappe.db.exists("Workspace", data.get("title"))
            or frappe.db.exists("Workspace", data.get("label"))
        )
        if not duplicate_workspace:
            raise
        workspace = frappe.get_doc("Workspace", duplicate_workspace)
        _clear_workspace_child_tables(workspace)
        workspace.update(data)
        _sanitize_workspace_links(workspace)
        _sanitize_workspace_shortcuts(workspace)
        workspace.save(ignore_permissions=True)


def ensure_workspace_sidebar_records():
    if not frappe.db.exists("DocType", "Workspace Sidebar"):
        return

    sidebar_root = Path(frappe.get_app_path("erpnextswiss", "workspace_sidebar"))
    if not sidebar_root.exists():
        return

    for sidebar_file in sidebar_root.glob("*.json"):
        data = json.loads(sidebar_file.read_text(encoding="utf-8"))
        if data.get("doctype") != "Workspace Sidebar" or not data.get("name"):
            continue
        _upsert_workspace_sidebar_record(_prepare_workspace_sidebar_data(data))


def _prepare_workspace_sidebar_data(data):
    data = data.copy()
    for meta_field in ("creation", "modified", "modified_by", "owner"):
        data.pop(meta_field, None)
    data.setdefault("standard", 1)
    data["app"] = "erpnextswiss"
    return data


def _upsert_workspace_sidebar_record(data):
    if frappe.db.exists("Workspace Sidebar", data["name"]):
        sidebar = frappe.get_doc("Workspace Sidebar", data["name"])
        if sidebar.meta.has_field("items"):
            sidebar.set("items", [])
        sidebar.update(data)
        sidebar.save(ignore_permissions=True)
    else:
        frappe.get_doc(data).insert(ignore_permissions=True)


def ensure_desktop_icon_records():
    if not frappe.db.exists("DocType", "Desktop Icon"):
        return

    icon_root = Path(frappe.get_app_path("erpnextswiss", "desktop_icon"))
    if not icon_root.exists():
        return

    for icon_file in icon_root.glob("*.json"):
        data = json.loads(icon_file.read_text(encoding="utf-8"))
        if data.get("doctype") != "Desktop Icon" or not data.get("name"):
            continue
        for meta_field in ("creation", "modified", "modified_by", "owner"):
            data.pop(meta_field, None)
        data.setdefault("standard", 1)
        data["app"] = "erpnextswiss"
        _upsert_desktop_icon_record(data)


def _upsert_desktop_icon_record(data):
    if frappe.db.exists("Desktop Icon", data["name"]):
        desktop_icon = frappe.get_doc("Desktop Icon", data["name"])
        if desktop_icon.meta.has_field("roles"):
            desktop_icon.set("roles", [])
        desktop_icon.update(data)
        desktop_icon.save(ignore_permissions=True)
    else:
        frappe.get_doc(data).insert(ignore_permissions=True)


def _sanitize_workspace_links(workspace):
    links = workspace.get("links") or []
    filtered_links = []
    for link in links:
        if link.get("link_type") == "Workspace":
            if hasattr(link, "link_type"):
                link.link_type = "URL"
                link.link_to = _workspace_route_url(link.get("link_to") or link.get("label"))
            else:
                link["link_type"] = "URL"
                link["link_to"] = _workspace_route_url(link.get("link_to") or link.get("label"))
        if link.get("link_type") == "URL":
            continue
        filtered_links.append(link)
    if hasattr(workspace, "links"):
        workspace.links = filtered_links
    else:
        workspace["links"] = filtered_links


def _sanitize_workspace_shortcuts(workspace):
    for shortcut in workspace.get("shortcuts") or []:
        if shortcut.get("type") == "Workspace":
            url = _workspace_route_url(shortcut.get("link_to") or shortcut.get("label"))
            if hasattr(shortcut, "type"):
                shortcut.type = "URL"
                shortcut.url = url
                shortcut.link_to = ""
                shortcut.doc_view = ""
            else:
                shortcut["type"] = "URL"
                shortcut["url"] = url
                shortcut["link_to"] = ""
                shortcut["doc_view"] = ""
        if shortcut.get("type") == "URL":
            if hasattr(shortcut, "link_to"):
                shortcut.link_to = ""
                if not shortcut.get("url"):
                    shortcut.url = _workspace_route_url(shortcut.get("label"))
            else:
                shortcut["link_to"] = ""
                shortcut.setdefault("url", _workspace_route_url(shortcut.get("label")))
        if shortcut.get("type") == "Report" and shortcut.get("doc_view") == "Report":
            if hasattr(shortcut, "doc_view"):
                shortcut.doc_view = ""
            else:
                shortcut["doc_view"] = ""


def _clear_workspace_child_tables(workspace):
    for fieldname in ("charts", "shortcuts", "links", "quick_lists", "number_cards", "custom_blocks", "roles"):
        if workspace.meta.has_field(fieldname):
            workspace.set(fieldname, [])


def _workspace_route_url(label):
    return "/desk/" + _workspace_route(label)


def _workspace_route(label):
    label = label or ""
    return WORKSPACE_ROUTES.get(label) or _slugify_route(label)


def _slugify_route(value):
    value = str(value or "").strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "é": "e",
        "è": "e",
        "à": "a",
        "ß": "ss",
        "&": " ",
        "+": " ",
        "/": " ",
        "\\": " ",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "workspace"


def _clear_desk_navigation_cache():
    frappe.clear_cache()
    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_key("bootinfo")
    
