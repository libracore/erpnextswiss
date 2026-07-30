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
@frappe.whitelist(methods=["POST"])
def unlink_asset(asset_name):
    if frappe.db.exists("Asset", asset_name):
        asset = frappe.get_doc("Asset", asset_name)
        asset.check_permission("write")
        asset.db_set({
            "purchase_invoice": None,
            "purchase_receipt": None,
        })
    return
