# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
from frappe import _

def get_data():
    return {
        'fieldname': 'ebics_connection',
        'transactions': [
            {
                'label': _('Transactions'),
                'items': ['ebics Statement']
            }
        ]
    }
