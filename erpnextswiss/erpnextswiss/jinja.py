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
