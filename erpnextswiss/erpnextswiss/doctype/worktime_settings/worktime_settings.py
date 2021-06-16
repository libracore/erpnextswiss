# -*- coding: utf-8 -*-
# Copyright (c) 2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class WorktimeSettings(Document):
    pass

@frappe.whitelist()
def get_daily_working_hours(company=None):
    if not company:
        company = frappe.defaults.get_global_default('company')
    hours = frappe.db.sql("""SELECT `daily_hours`
                     FROM `tabDaily Hours` 
                     WHERE `company` = "{c}";""".format(c=company), as_dict=True)
    if hours and len(hours) > 0:
        return hours[0]['daily_hours']
    else:
        return 8
