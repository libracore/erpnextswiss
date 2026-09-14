"""Move legacy Page proxies out of Workspace routes, preserving their history."""

import frappe


WORKSPACE_ROUTE_PAGES = {
    "erpnextswiss": "Schweizer Buchhaltung",
    "schweizer-buchhaltung": "Schweizer Buchhaltung",
    "zahlungsverkehr": "Zahlungsverkehr",
    "qr-rechnung-e-rechnung": "QR-Rechnung & E-Rechnung",
    "schweizer-mwst": "Schweizer MwSt",
    "schweiz-einstellungen": "Schweiz-Einstellungen",
}
LEGACY_PAGE_ROLES = {"System Manager", "Accounts Manager", "Accounts User"}


def retire_workspace_route_pages():
    """Use native rename so roles, versions, attachments and links survive upgrades."""
    from frappe.desk.utils import slug
    from frappe.model.rename_doc import rename_doc

    frappe.only_for("System Manager")
    # Match Frappe's route namespace even during migration, when the normal
    # document validator deliberately skips this check.
    page_routes = {slug(name) for name in frappe.get_all("Page", pluck="name")}
    reserved_routes = {
        slug(name) for doctype in ("Workspace", "DocType")
        for name in frappe.get_all(doctype, pluck="name")
    }
    candidates = []
    for name, title in WORKSPACE_ROUTE_PAGES.items():
        if not frappe.db.exists("Page", name):
            continue
        frappe.db.get_value("Page", name, for_update=True)
        page = frappe.get_doc("Page", name)
        _validate_owned_proxy(page, title)
        target = retired_route_page_name(name)
        target_route = slug(target)
        if target_route in reserved_routes:
            frappe.throw(frappe._("Legacy workspace Page target already exists: {0}").format(
                target), frappe.ValidationError)
        if frappe.db.exists("Page", target):
            frappe.db.get_value("Page", target, for_update=True)
            _validate_retired_proxy(frappe.get_doc("Page", target), title)
            candidates.append((name, target, True))
        elif target_route in page_routes:
            frappe.throw(frappe._("Legacy workspace Page target already exists: {0}").format(
                target), frappe.ValidationError)
        else:
            candidates.append((name, target, False))

    # First upgrades use native rename. Repeat upgrades may see Frappe-created
    # standard proxy records again; merge those owned records back into the
    # already-retired Page so links, versions, attachments and comments survive.
    for name, target, merge in candidates:
        if merge:
            _preserve_missing_roles(frappe.get_doc("Page", name), frappe.get_doc("Page", target))
        rename_doc("Page", name, target, force=True, merge=merge,
                   ignore_permissions=True, show_alert=False, rebuild_search=False)
        retained = frappe.get_doc("Page", target)
        retained.standard = "No"
        retained.flags.do_not_update_json = True
        retained.save(ignore_permissions=True)
    return [name for name, _target, _merge in candidates]


def retired_route_page_name(name):
    return "kt-swiss-route-" + name


def _validate_owned_proxy(page, title):
    expected = {
        "module": "ERPNextSwiss", "standard": "Yes", "page_name": page.name, "title": title,
    }
    if (any(page.get(field) != value for field, value in expected.items())
            or page.get("system_page") or page.get("restrict_to_domain")):
        _refuse_customized_proxy(page.name)


def _validate_retired_proxy(page, title):
    expected = {
        "module": "ERPNextSwiss", "standard": "No", "page_name": page.name, "title": title,
    }
    if (any(page.get(field) != value for field, value in expected.items())
            or page.get("system_page") or page.get("restrict_to_domain")):
        _refuse_customized_proxy(page.name)


def _preserve_missing_roles(source, target):
    source_roles = [row.role for row in source.get("roles") or [] if row.role]
    target_roles = {row.role for row in target.get("roles") or [] if row.role}
    changed = False
    for role in source_roles:
        if role in target_roles:
            continue
        target.append("roles", {"role": role})
        target_roles.add(role)
        changed = True
    if changed:
        target.flags.do_not_update_json = True
        target.save(ignore_permissions=True)


def _refuse_customized_proxy(name):
    frappe.throw(
        frappe._("Workspace redirect Page {0} was customized. Review and preserve its configuration before upgrading.").format(name),
        frappe.ValidationError,
    )
