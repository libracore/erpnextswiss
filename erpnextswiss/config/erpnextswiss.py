from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
        {
            "label": _("Banking"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "page",
                       "name": "bankimport",
                       "label": _("Bank import"),
                       "description": _("Bank import")
                   },
                   {
                       "type": "page",
                       "name": "match_payments",
                       "label": _("Match payments"),
                       "description": _("Match payments")
                   },
                   {
                       "type": "page",
                       "name": "payment_export",
                       "label": _("Payment export"),
                       "description": _("Payment export")
                   }
            ]
        },
        {
            "label": _("Taxes"),
            "icon": "fa fa-bank",
            "items": [
                   {
                       "type": "doctype",
                       "name": "VAT Declaration",
                       "label": _("VAT Declaration"),
                       "description": _("VAT Declaration")
                   }
            ]
        },
        {
            "label": _("Human Resources"),
            "icon": "fa fa-users",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Salary Certificate",
                       "label": _("Salary Certificate"),
                       "description": _("Salary Certificate")
                   }
            ]
        },
        {
            "label": _("Configuration"),
            "icon": "fa fa-bank",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Label Printer",
                       "label": _("Label Printer"),
                       "description": _("Label Printer")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Pincode",
                       "label": _("Pincode"),
                       "description": _("Pincode")                   
                   }                   
            ]
        },
        {
            "label": _("Integrations"),
            "icon": "octicon octicon-git-compare",
            "items": [
                   {
                       "type": "page",
                       "name": "abacus_export",
                       "label": _("Abacus Export"),
                       "description": _("Abacus Export")                   
                   }                   
            ]
        },
    ]
