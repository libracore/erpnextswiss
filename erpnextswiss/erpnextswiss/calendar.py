# Copyright (c) 2023, libracore and Contributors
# License: GNU General Public License v3. See license.txt
#
#
# This is a web scraper to read public holidays from the internet
#
# Execute manually from
#
#  $ bench execute erpnextswiss.erpnextswiss.calendar.parse_holidays --kwargs "{'region': 'ZH', 'year': '2023'}"
#

from __future__ import unicode_literals
import frappe
from frappe import _
from bs4 import BeautifulSoup
import requests

REGIONS = {
    'WT': '3032',
    'ZH': '2872',
    'AG': '1',
    'AR': '245',
    'AI': '266',
    'BL': '273',
    'BS': '365',
    'BE': '369',
    'FR': '796',
    'GE': '1026',
    'GL': '1072',
    'GR': '1102',
    'JU': '1323',
    'LU': '1410',
    'NE': '1523',
    'NW': '1592',
    'OW': '1604',
    'SH': '1612',
    'SZ': '1653',
    'SO': '1690',
    'SG': '1827',
    'TI': '1932',
    'TG': '2173',
    'UR': '2262',
    'VD': '2283',
    'VS': '2685',
    'ZG': '2860'
}

HOST = "https://www.feiertagskalender.ch/index.php"

@frappe.whitelist()
def parse_holidays(region, year):
    # find data source
    r = requests.get("{0}?geo={1}&klasse=3&jahr={2}&hl=de".format(
        HOST, 
        REGIONS[region] if region in REGIONS else REGIONS['ZH'], 
        year
    ))
    data = r.text
    
    # parse content
    soup = BeautifulSoup(data, 'html.parser')
    rows = soup.find_all("tr")
    holidays = []
    for row in rows:
        columns = row.find_all("td")
        if len(columns) == 5:
            date = columns[0].get_text()                        # comes as DD.MM.YYYY
            description = columns[2].get_text().strip()         # description
            holidays.append({
                'date': date,
                'description': description
            })
            #print("{0}: {1}".format(date, description))
        
    return holidays
