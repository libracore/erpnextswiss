# -*- coding: utf-8 -*-
#
# esr_qr_tools.py
#
# Copyright (C) libracore, 2017-2025
# https://www.libracore.com or https://github.com/libracore
#

import frappe
from frappe import _
import re

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

"""
This function will extract the first numeric block from the document name (exclude revision index)
and add it up to 26 digits.
"""
@frappe.whitelist()
def get_esr_raw_from_document_name(document_name):
    match = re.search(r'-(\d+)-', document_name)
    reference_raw = (match.group(1)).rjust(26, "0")
    return reference_raw

"""
This function takes a 26 digit reference raw and adds the check digit.
It can format it into the usual form with whitespaces (default)
""" 
@frappe.whitelist()
def add_check_digit_to_esr_reference(reference_raw, formatted=True):

    check_digit_matrix = {
        '0': [0, 9, 4, 6, 8, 2, 7, 1, 3, 5, 0],
        '1': [9, 4, 6, 8, 2, 7, 1, 3, 5, 0, 9],
        '2': [4, 6, 8, 2, 7, 1, 3, 5, 0, 9, 8],
        '3': [6, 8, 2, 7, 1, 3, 5, 0, 9, 4, 7],
        '4': [8, 2, 7, 1, 3, 5, 0, 9, 4, 6, 6],
        '5': [2, 7, 1, 3, 5, 0, 9, 4, 6, 8, 5],
        '6': [7, 1, 3, 5, 0, 9, 4, 6, 8, 2, 4],
        '7': [1, 3, 5, 0, 9, 4, 6, 8, 2, 7, 3],
        '8': [3, 5, 0, 9, 4, 6, 8, 2, 7, 1, 2],
        '9': [5, 0, 9, 4, 6, 8, 2, 7, 1, 3, 1]
    }
    
    transfer = 0
    check_digit = 0
    reference_raw = reference_raw.replace(" ", "")
    for digit in reference_raw:
        digit = int(digit)
        transfer = int(check_digit_matrix[str(transfer)][digit])
    
    check_digit = int(check_digit_matrix[str(transfer)][10])
    
    qrr_reference = reference_raw + str(check_digit)

    if formatted:
        qrr_reference = "{0} {1} {2} {3} {4} {5}".format(
            qrr_reference[:2],
            qrr_reference[2:7],
            qrr_reference[7:12],
            qrr_reference[12:17],
            qrr_reference[17:22],
            qrr_reference[22:27]
        )

    return qrr_reference