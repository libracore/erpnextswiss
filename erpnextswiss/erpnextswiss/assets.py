# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe

"""
This function allows to scrap an asset CH/AT-style, dated with yearly accumulated reconiliation
"""
@frappe.whitelist(methods=["POST"])
def smart_scrap(asset, date):
    asset_doc = frappe.get_doc("Asset", asset)
    asset_doc.check_permission("write")
    asset_doc.db_set({
        "disposal_date": date,
        "status": "Scrapped",
    })
    return
