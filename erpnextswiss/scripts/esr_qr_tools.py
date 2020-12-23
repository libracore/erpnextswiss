# -*- coding: utf-8 -*-
#
# esr_qr_tools.py
#
# Copyright (C) libracore, 2017-2020
# https://www.libracore.com or https://github.com/libracore
#
# For information on ERPNext, refer to https://erpnext.org/
#

import frappe
from frappe import _

# fetch supplier based on participant number
@frappe.whitelist()
def get_data_based_on_esr(participant):
    default_item = frappe.get_single('ERPNextSwiss Settings').scanning_default_item
    if default_item:
        participant = participant.replace("", "%").replace("0", "")
        supplier = frappe.db.sql("""SELECT `name`, `supplier_name` FROM `tabSupplier` WHERE `esr_participation_number` LIKE '{participant}'""".format(participant=participant), as_dict=True)
        if len(supplier) > 0:
            if len(supplier) > 1:
                return {
                    'error': False,
                    'supplier': supplier,
                    'more_than_one_supplier': True,
                    'default_item': default_item
                }
            else:
                return {
                    'error': False,
                    'supplier': supplier[0].name,
                    'more_than_one_supplier': False,
                    'default_item': default_item
                }
        else:
            return {
                'error': _('Supplier with reference {0} not found. Please add a supplier with this participant ID.').format(participant),
                'supplier': False,
                'more_than_one_supplier': False,
                    'default_item': default_item
            }
    else:
        return {
                'error': _("""Default item not found. Please configure this in the <a href='/desk#Form/ERPNextSwiss Settings'>ERPNextSwiss settings</a>."""),
                'supplier': False,
                'more_than_one_supplier': False,
                'default_item': False
            }
