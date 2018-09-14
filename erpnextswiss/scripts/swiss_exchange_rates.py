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
from bs4 import BeautifulSoup
import frappe
from time import strftime
import requests

def parse_estv_xml(url, currencies):
    # import content into a string from URL XML data
    r = requests.get(url)
    data = r.text

    # parse string to an XML object
    root = BeautifulSoup(data, 'lxml')
    for currency in root.find_all('devise'):
        entry = BeautifulSoup(str(currency), 'lxml')
        name = entry.waehrung.get_text()
        for selected_currency in currencies:
            if selected_currency in name:
                rate = entry.kurs.get_text()
                print(name + " = " + rate + " CHF")
                create_exchange_rate(selected_currency, float(rate), "CHF")
    return
    
def read_rates(currencies=["EUR"]):
    parse_estv_xml('http://www.pwebapps.ezv.admin.ch/apps/rates/estv/getavgxml', currencies)
    return

def read_daily_rates(currencies=["EUR"]):
    parse_estv_xml('http://www.pwebapps.ezv.admin.ch/apps/rates/rate/getxml?activeSearchType=today', currencies)
    return

def create_exchange_rate(from_currency, rate, to_currency="CHF"):
    # insert a new record in ERPNext
    # Exchange Rate (1 EUR = [?] CHF)
    date = strftime("%Y-%m-%d")
    new_exchange_rate = frappe.get_doc({
        'doctype': "Currency Exchange",
        'date': date,
        'from_currency': from_currency,
        'to_currency': to_currency,
        'exchange_rate': rate
    })
    try:
        record = new_exchange_rate.insert()  
    except frappe.exceptions.DuplicateEntryError:
        print("There is already an exchange rate for {0} on {1}".format(from_currency, date))
        record = None
    except Exception as err:
        print(err.message)
        record = None
    return record
