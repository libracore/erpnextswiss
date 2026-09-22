#
# swiss_exchange_rates.py
#
# Copyright (C) libracore, 2017-2025
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
# Note: an exchange rate that has already been imported on the same day is skipped (not an error)
#
# Errors are recorded in the Error Log with a title starting with LOG_TITLE, so that
# callers (e.g. a scheduler job) can detect and report failures of a run.
#
from bs4 import BeautifulSoup
import frappe
from time import strftime
import requests

LOG_TITLE = "Swiss exchange rates"
REQUEST_TIMEOUT = 60

def log_rate_error(title, details=None):
    frappe.log_error(
        title="{0}: {1}".format(LOG_TITLE, title),
        message="{0}\n\n{1}".format(details or title, frappe.get_traceback())
    )
    print("ERROR: {0}".format(title))
    return

def parse_estv_xml(url, currencies):
    # import content into a string from URL XML data
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.text
    except Exception as err:
        log_rate_error("download failed", "Could not download exchange rates from {0}: {1}".format(url, err))
        return

    # parse string to an XML object
    root = BeautifulSoup(data, 'lxml')
    found_currencies = []
    for currency in root.find_all('devise'):
        entry = BeautifulSoup(str(currency), 'lxml')
        try:
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
                    found_currencies.append(selected_currency)
                    create_exchange_rate(selected_currency, float(equal_rate), "CHF")
        except Exception as err:
            log_rate_error("invalid entry", "Could not parse entry from {0}: {1}\n\n{2}".format(url, err, currency))

    missing_currencies = [c for c in currencies if c not in found_currencies]
    if missing_currencies:
        log_rate_error("currency not found",
            "No exchange rate for {0} found in {1}. Response (first 2000 characters):\n\n{2}".format(
                ", ".join(missing_currencies), url, data[:2000]))
    return

def read_rates(currencies=["EUR"]):
    parse_estv_xml('https://www.backend-rates.bazg.admin.ch/api/xmlavgmonth', currencies)
    return

def read_daily_rates(currencies=["EUR"]):
    parse_estv_xml('https://www.backend-rates.bazg.admin.ch/api/xmldaily', currencies)
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
        log_rate_error("could not create exchange rate",
            "Could not create exchange rate {0} -> {1} ({2}) on {3}: {4}".format(
                from_currency, to_currency, rate, date, err))
        record = None
    return record

"""
Get the latest known rate of currency -> CHF, None if there is none
"""
def get_latest_chf_rate(currency):
    rates = frappe.db.sql("""
        SELECT `exchange_rate`
        FROM `tabCurrency Exchange`
        WHERE
            `from_currency` = %(f)s
            AND `to_currency` = "CHF"
        ORDER BY `date` DESC
        LIMIT 1;""", {'f': currency}, as_dict=True)
    if len(rates) > 0 and rates[0]['exchange_rate']:
        return rates[0]['exchange_rate']
    else:
        return None

"""
Import the reverse rate
"""
def add_inverted_rates(currencies=["EUR"]):
    from_currency = "CHF"

    for currency in currencies:
        base_rate = get_latest_chf_rate(currency)
        if not base_rate:
            log_rate_error("inverted rate not possible",
                "Cannot add inverted rate CHF -> {0}: no exchange rate {0} -> CHF found".format(currency))
            continue

        create_exchange_rate(from_currency, float(1/base_rate), currency)

    return

"""
Import the cross rate
"""
def add_cross_rates(from_currency="USD", to_currency="EUR"):
    from_rate = get_latest_chf_rate(from_currency)
    to_rate = get_latest_chf_rate(to_currency)

    missing_currencies = [c for c, r in ((from_currency, from_rate), (to_currency, to_rate)) if not r]
    if missing_currencies:
        log_rate_error("cross rate not possible",
            "Cannot add cross rate {0} -> {1}: no exchange rate to CHF found for {2}".format(
                from_currency, to_currency, ", ".join(missing_currencies)))
        return

    create_exchange_rate(from_currency, float(from_rate/to_rate), to_currency)

    return
