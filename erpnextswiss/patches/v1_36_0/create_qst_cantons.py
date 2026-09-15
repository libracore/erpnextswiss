import frappe

CANTONS = {
    "AG": "Aargau", "AI": "Appenzell Innerrhoden", "AR": "Appenzell Ausserrhoden", "BE": "Bern",
    "BL": "Basel-Landschaft", "BS": "Basel-Stadt", "FR": "Freiburg", "GE": "Genf", "GL": "Glarus",
    "GR": "Graubünden", "JU": "Jura", "LU": "Luzern", "NE": "Neuenburg", "NW": "Nidwalden", "OW": "Obwalden",
    "SG": "St. Gallen", "SH": "Schaffhausen", "SO": "Solothurn", "SZ": "Schwyz", "TG": "Thurgau", "TI": "Tessin",
    "UR": "Uri", "VD": "Waadt", "VS": "Wallis", "ZG": "Zug", "ZH": "Zürich",
}
ANNUAL_MODEL = ("FR", "GE", "TI", "VD", "VS")


def execute():
    frappe.reload_doc("erpnextswiss", "doctype", "qst_canton")
    for canton, canton_name in CANTONS.items():
        if not frappe.db.exists("QST Canton", canton):
            frappe.get_doc({
                "doctype": "QST Canton",
                "canton": canton,
                "canton_name": canton_name,
                "calculation_model": "Annual" if canton in ANNUAL_MODEL else "Monthly",
            }).insert(ignore_permissions=True)
