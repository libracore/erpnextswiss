import frappe


def is_enabled():
    """True if the Quellensteuer module is enabled."""
    return bool(frappe.db.get_single_value("QST Settings", "enabled"))
