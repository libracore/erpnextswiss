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
                       "label": "Bank Import",
                       "description": _("Bank import")
                   },
                                      {
                       "type": "page",
                       "name": "payment_export",
                       "label": "Payment export",
                       "description": _("Payment export")
                   }
            ]
        },
        {
            "label": _("VAT"),
            "icon": "fa fa-bank",
            "items": [
                   {
                       "type": "doctype",
                       "name": "VAT Declaration",
                       "label": "VAT Declaration",
                       "description": _("VAT Declaration")
                   }
            ]
        },
    ]
