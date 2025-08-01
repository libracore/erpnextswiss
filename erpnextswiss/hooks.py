# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "erpnextswiss"
app_title = "ERPNextSwiss"
app_publisher = "libracore (https://www.libracore.com)"
app_description = "ERPNext application for Switzerland-specific use cases"
app_icon = "fa fa-diamond"
app_color = "#92d050"
app_email = "info@libracore.com"
app_license = "AGPL"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnextswiss/css/erpnextswiss.css"
app_include_js = [
    "/assets/erpnextswiss/js/swiss_common.js",
    "/assets/erpnextswiss/js/iban.js",
    "/assets/erpnextswiss/js/email.js",
    "assets/js/erpnextswiss_templates.min.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/erpnextswiss/css/erpnextswiss.css"
# web_include_js = "/assets/erpnextswiss/js/erpnextswiss.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Item" :            "public/js/item.js",
    "Quotation" :       "public/js/quotation.js",
    "Sales Order" :     "public/js/sales_order.js",
    "Sales Invoice" :   "public/js/sales_invoice.js",
    "Purchase Invoice" :   "public/js/purchase_invoice.js",
    "Fiscal Year":      "public/js/fiscal_year.js",
    "Supplier":         "public/js/supplier.js",
    "Customer":         "public/js/customer.js",
    "Address":          "public/js/address.js",
    "Holiday List":     "public/js/holiday_list.js",
    "Shipment":         "public/js/shipment.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
doctype_list_js = {
    "Purchase Invoice" : "public/js/purchase_invoice_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# adding Jinja environments
jenv = {
    "methods": [
        "get_tax_details:erpnextswiss.erpnextswiss.report.kontrolle_mwst.kontrolle_mwst.get_data",
        "get_account_sheets:erpnextswiss.erpnextswiss.finance.get_account_sheets",
        "get_customer_ledger:erpnextswiss.erpnextswiss.finance.get_customer_ledger",
        "get_week_from_date:erpnextswiss.erpnextswiss.jinja.get_week_from_date",
        "strip_html:erpnextswiss.erpnextswiss.jinja.strip_html",
        "get_accounts_receivable:erpnextswiss.erpnextswiss.jinja.get_accounts_receivable",
        "get_primary_company_address:erpnextswiss.scripts.crm_tools.get_primary_company_address",
        "get_primary_customer_address:erpnextswiss.scripts.crm_tools.get_primary_customer_address",
        "get_primary_supplier_address:erpnextswiss.scripts.crm_tools.get_primary_supplier_address",
        "get_vat_control_details:erpnextswiss.erpnextswiss.report.kontrolle_mwst.kontrolle_mwst.get_vat_control_details",
        "get_planzer_barcode:erpnextswiss.erpnextswiss.planzer.get_planzer_barcode",
        "get_planzer_qr_code:erpnextswiss.erpnextswiss.planzer.get_planzer_qr_code"
    ]
}

# allow to link incoing mails to EDI File
email_append_to = ["EDI File"]

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#    "Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "erpnextswiss.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "erpnextswiss.install.before_install"
after_install = "erpnextswiss.setup.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnextswiss.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#     "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#     "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#     "*": {
#         "on_update": "method",
#         "on_cancel": "method",
#         "on_trash": "method"
#    }
# }
doc_events = {
    "Contact": {
        "on_update": "erpnextswiss.erpnextswiss.nextcloud.contacts.send_contact_to_nextcloud",
        "on_trash": "erpnextswiss.erpnextswiss.nextcloud.contacts.delete_contact_from_nextcloud"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#     "all": [
#         "erpnextswiss.tasks.all"
#     ],
#     "daily": [
#         "erpnextswiss.tasks.daily"
#     ],
#     "hourly": [
#         "erpnextswiss.tasks.hourly"
#     ],
#     "weekly": [
#         "erpnextswiss.tasks.weekly"
#     ]
#     "monthly": [
#         "erpnextswiss.tasks.monthly"
#     ]
# }
scheduler_events = {
    "daily": [
        "erpnextswiss.erpnextswiss.doctype.inspection_equipment.inspection_equipment.check_calibration_status",
        "erpnextswiss.erpnextswiss.ebics.sync"
    ],
    "hourly": [
        "erpnextswiss.erpnextswiss.edi.process_incoming"
    ]
}

# Testing
# -------

# before_tests = "erpnextswiss.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
#     "frappe.desk.doctype.event.event.get_events": "erpnextswiss.event.get_events"
# }

# Fixtures (to import DocType customisations)
# --------
fixtures = ["Custom Field"]

domains = {
    'HLK': 'erpnextswiss.domains.hlk'
}
