# -*- coding: utf-8 -*-
#
# esr_qr_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
#

import frappe
from frappe import _

# fetch supplier based on participant number
@frappe.whitelist()
def get_supplier_based_on_esr(participant):
    participant_to_search = participant.replace("", "%").replace("0", "")
    supplier = frappe.db.sql("""SELECT `name`, `supplier_name` FROM `tabSupplier` WHERE `esr_participation_number` LIKE '{participant}'""".format(participant=participant_to_search), as_dict=True)
    if len(supplier) > 0:
        if len(supplier) > 1:
            return {
                'error': False,
                'supplier': supplier,
                'more_than_one_supplier': True
            }
        else:
            return {
                'error': False,
                'supplier': supplier[0].name,
                'supplier_name': supplier[0].supplier_name,
                'more_than_one_supplier': False
            }
    else:
        return {
            'error': True,
            'supplier': False,
            'more_than_one_supplier': False
        }

# fetch default_item from settings
@frappe.whitelist()
def check_defaults():
    defaults = {}
    missing_values = []
    settings = frappe.get_single('ERPNextSwiss Settings')
    
    positive_deviation = settings.scanning_default_positive_deviation
    defaults['positive_deviation'] = positive_deviation
    negative_deviation = settings.scanning_default_negative_deviation
    defaults['negative_deviation'] = negative_deviation
    
    default_item = settings.scanning_default_item
    if default_item:
        defaults['default_item'] = default_item
    else:
        missing_values.append(_("Default Item"))
    
    positive_deviation_item = settings.scanning_default_positive_deviation_item
    if positive_deviation_item:
        defaults['positive_deviation_item'] = positive_deviation_item
    else:
        missing_values.append(_("Default Positive Deviation Item"))
    
    supplier = settings.scanning_default_supplier
    if supplier:
        defaults['supplier'] = supplier
    else:
        missing_values.append(_("Default Supplier"))
        
    default_tax_rate = settings.scanning_default_tax_rate
    if default_tax_rate:
        defaults['default_tax_rate'] = default_tax_rate
    else:
        missing_values.append(_("Default Tax Rate"))
        
    if len(missing_values) > 0:
        return {'error': _("""{missing_values} not found. Please configure this in the <a href='/desk#Form/ERPNextSwiss Settings'>ERPNextSwiss settings</a>.""").format(missing_values=', '.join(missing_values))}
    else:
        return defaults