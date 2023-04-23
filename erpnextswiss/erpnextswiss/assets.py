# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe

"""
This function allows to scrap an asset CH/AT-style, dated with yearly accumulated reconiliation
"""
@frappe.whitelist()
def smart_scrap(asset, date):
    frappe.db.sql("""UPDATE `tabAsset`
                        SET `disposal_date` = "{date}", `status` = "Scrapped"
                        WHERE `name` = "{asset}";""".format(asset=asset, date=date))
    return
