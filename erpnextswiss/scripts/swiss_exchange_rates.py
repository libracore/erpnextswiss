#
# swiss_exchange_rates.py
#
# Copyright (C) libracore, 2017
# https://www.libracore.com or https://github.com/libracore
#
# For information on ERPNext, refer to https://erpnext.org/
#
# Execute with 
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.read_rates
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.read_rates --kwargs "{'currencies': ['EUR', 'USD', 'GBP']}"
#
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.read_daily_rates
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.read_daily_rates --kwargs "{'currencies': ['EUR', 'USD', 'GBP']}"
#
# Note: throws an error if the same currency exchange rate has been imported already on the same day
#
#Python 3: from urllib.request import urlopen
import urllib2
import xml.etree.ElementTree as ET
import frappe
from time import strftime

def read_rates(currencies=["EUR"]):
    # import content into a string from URL XML data
    # in Python 3, use urllib.request
    url = "http://www.afd.admin.ch/publicdb/newdb/mwst_kurse/estv/mittelkurse_xml.php"
    #Python 3: html = urlopen(url)
    html = urllib2.urlopen(url)
    data = html.read()
    html.close()

    # parse string to an XML object
    # Refer to https://docs.python.org/2/library/xml.etree.elementtree.html
    root = ET.fromstring(data)
    # debug
    # for child in root:
    #     print(child.tag, child.attrib)
    # Note: xml uses an xsl template
    for currency in root.findall('{http://www.afd.admin.ch/publicdb/newdb/mwst_mittelkurse}devise'):
        name = currency.find('{http://www.afd.admin.ch/publicdb/newdb/mwst_mittelkurse}waehrung')
        for selected_currency in currencies:
            if selected_currency in name.text:
                rate = currency.find('{http://www.afd.admin.ch/publicdb/newdb/mwst_mittelkurse}kurs')
                print(name.text + " = " + rate.text + " CHF")

                # insert a new record in ERPNext
                new_exchange_rate = frappe.get_doc({"doctype": "Currency Exchange"})
                new_exchange_rate.date = strftime("%Y-%m-%d")
                new_exchange_rate.from_currency = selected_currency
                new_exchange_rate.to_currency = "CHF"
                # Exchange Rate (1 EUR = [?] CHF)
                new_exchange_rate.exchange_rate = float(rate.text)
                new_exchange_rate.insert()    

def read_daily_rates(currencies=["EUR"]):
    # import content into a string from URL XML data
    # in Python 3, use urllib.request
    url = "http://www.pwebapps.ezv.admin.ch/apps/rates/rate/getxml?activeSearchType=today"
    #Python 3: html = urlopen(url)
    html = urllib2.urlopen(url)
    data = html.read()
    html.close()

    # parse string to an XML object
    # Refer to https://docs.python.org/2/library/xml.etree.elementtree.html
    root = ET.fromstring(data)
    # Note: xml uses an xsl template
    for currency in root.findall('{http://www.pwebapps.ezv.admin.ch/apps/rates}devise'):
        name = currency.find('{http://www.pwebapps.ezv.admin.ch/apps/rates}waehrung')
        for selected_currency in currencies:
            if selected_currency in name.text:
                rate = currency.find('{http://www.pwebapps.ezv.admin.ch/apps/rates}kurs')
                print(name.text + " = " + rate.text + " CHF")

                # insert a new record in ERPNext
                new_exchange_rate = frappe.get_doc({"doctype": "Currency Exchange"})
                new_exchange_rate.date = strftime("%Y-%m-%d")
                new_exchange_rate.from_currency = selected_currency
                new_exchange_rate.to_currency = "CHF"
                # Exchange Rate (1 EUR = [?] CHF)
                new_exchange_rate.exchange_rate = float(rate.text)
                new_exchange_rate.insert()  
