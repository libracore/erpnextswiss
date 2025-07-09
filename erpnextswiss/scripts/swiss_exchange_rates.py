#
# swiss_exchange_rates.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
#
# Execute with 
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.read_rates
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.read_rates --kwargs "{'currencies': ['EUR', 'USD', 'GBP']}"
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.add_inverted_rates --kwargs "{'currencies': ['EUR', 'USD', 'GBP']}"
#    $ bench execute erpnextswiss.scripts.swiss_exchange_rates.add_cross_rates --kwargs "{'from_currency': 'USD', 'to_currency': 'EUR'}"
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
                # get devisor in case of non-equal currencies (e.g. 100 JPY = .. CHF)
                try:
                    divisor = float(name.split(" ")[0])
                except:
                    divisor = 1
                rate = entry.kurs.get_text()
                equal_rate = float(rate) / divisor
                print("{0} = {1} CHF ({2})".format(name, rate, equal_rate))
                create_exchange_rate(selected_currency, float(equal_rate), "CHF")
    return
    
def read_rates(currencies=["EUR"]):
    parse_estv_xml('https://www.backend-rates.ezv.admin.ch/api/xmlavgmonth', currencies)
    return

def read_daily_rates(currencies=["EUR"]):
    parse_estv_xml('https://www.backend-rates.ezv.admin.ch/api/xmldaily', currencies)
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

"""
Import the reverse rate
"""
def add_inverted_rates(currencies=["EUR"]):
    from_currency = "CHF"
    
    for currency in currencies:
        base_rates = frappe.db.sql("""
            SELECT `exchange_rate`
            FROM `tabCurrency Exchange`
            WHERE 
                `from_currency` = "{f}"
                AND `to_currency` = "{t}"
            ORDER BY `date` DESC
            LIMIT 1;""".format(f=currency, t=from_currency), as_dict=True)
        if len(base_rates) > 0:
            base_rate = base_rates[0]['exchange_rate']
        else:
            base_rate = 1
            
        create_exchange_rate(from_currency, float(1/base_rate), currency)
    
    return
    
"""
Import the cross rate
"""
def add_cross_rates(from_currency="USD", to_currency="EUR"):
    from_rates = frappe.db.sql("""
        SELECT `exchange_rate`
        FROM `tabCurrency Exchange`
        WHERE 
            `from_currency` = "{f}"
            AND `to_currency` = "CHF"
        ORDER BY `date` DESC
        LIMIT 1;""".format(f=from_currency), as_dict=True)
    if len(from_rates) > 0:
        from_rate = from_rates[0]['exchange_rate']
    else:
        from_rate = 1
    
    to_rates = frappe.db.sql("""
        SELECT `exchange_rate`
        FROM `tabCurrency Exchange`
        WHERE 
            `from_currency` = "{f}"
            AND `to_currency` = "CHF"
        ORDER BY `date` DESC
        LIMIT 1;""".format(f=to_currency), as_dict=True)
    if len(to_rates) > 0:
        to_rate = to_rates[0]['exchange_rate']
    else:
        to_rate = 1
        
    create_exchange_rate(from_currency, float(from_rate/to_rate), to_currency)
    
    return
