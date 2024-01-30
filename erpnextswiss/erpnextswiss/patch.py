# Copyright (c) 2023, libracore and contributors
# For license information, please see license.txt

import frappe

"""
This patch will set Email to all notifications without a channel.
Using that, they can be disabled.

Run as 
 $ bench execute erpnextswiss.erpnextswiss.patch.patch_old_notification_channels
 
"""
def patch_old_notification_channels():
    frappe.db.sql("""UPDATE `tabNotification` SET `channel` = "Email" WHERE `channel` IS NULL;""")
    return
