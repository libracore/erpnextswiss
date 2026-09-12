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
    routes = {slug(name) for doctype in ("Page", "Workspace", "DocType")
              for name in frappe.get_all(doctype, pluck="name")}
    candidates = []
    for name, title in WORKSPACE_ROUTE_PAGES.items():
        if not frappe.db.exists("Page", name):
            continue
        frappe.db.get_value("Page", name, for_update=True)
        page = frappe.get_doc("Page", name)
        _validate_owned_proxy(page, title)
        if slug(retired_route_page_name(name)) in routes:
            frappe.throw(frappe._("Legacy workspace Page target already exists: {0}").format(
                retired_route_page_name(name)), frappe.ValidationError)
        candidates.append(name)

    # Never merge, delete, recreate or bypass rename validation. Source files for
    # the technical Page names keep previously linked Page references functional.
    for name in candidates:
        rename_doc("Page", name, retired_route_page_name(name), force=True,
                   ignore_permissions=True, show_alert=False, rebuild_search=False)
        retained = frappe.get_doc("Page", retired_route_page_name(name))
        retained.standard = "No"
        retained.flags.do_not_update_json = True
        retained.save(ignore_permissions=True)
    return candidates


def retired_route_page_name(name):
    return "kt-swiss-route-" + name


def _validate_owned_proxy(page, title):
    expected = {
        "module": "ERPNextSwiss", "standard": "Yes", "page_name": page.name, "title": title,
    }
    if (any(page.get(field) != value for field, value in expected.items())
            or page.get("system_page") or page.get("restrict_to_domain")):
        _refuse_customized_proxy(page.name)


def _refuse_customized_proxy(name):
    frappe.throw(
        frappe._("Workspace redirect Page {0} was customized. Review and preserve its configuration before upgrading.").format(name),
        frappe.ValidationError,
    )
