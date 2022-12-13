# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
import re
import datetime

CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

""" Jinja hook to strip html from string """
def strip_html(s):
    cleantext = re.sub(CLEANR, '', s)
    return cleantext

def get_week_from_date(date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
    return date.isocalendar()[1]

""" Jinja hook to get accounts receivable """
def get_accounts_receivable(customer):
    from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
    args = {
        'party_type': "Customer",
        'naming_by': ["Selling Settings", "cust_master_name"],
        'range1': 30,
        'range2': 60,
        'range3': 90,
        'range4':120
    }
    filters = {
        'customer': customer
    }
    raw = ReceivablePayableReport(filters).run(args)
    try:
        # extract relevant data
        data = raw[1]
        return data
    except:
        return []
