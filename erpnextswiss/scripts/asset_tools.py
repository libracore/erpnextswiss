# -*- coding: utf-8 -*-
#
# asset_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
#

import frappe

"""
This function will allow to unlink an asset from PREC and PINV, because otherwise there is a dead-link

Run from console using unlink_asset();
"""
@frappe.whitelist()
def unlink_asset(asset_name):
    if frappe.db.exists("Asset", asset_name):
        frappe.db.sql("""
            UPDATE `tabAsset`
            SET `purchase_invoice` = NULL, `purchase_receipt` = NULL
            WHERE `name` = "{asset_name}";
        """.format(asset_name=asset_name))
        frappe.db.commit()
    return
