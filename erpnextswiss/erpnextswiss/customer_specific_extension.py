# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
import math
from bs4 import BeautifulSoup
from frappe.utils.data import getdate

@frappe.whitelist()
def deactiviate_pricing_rule(sinv, short=0, long=0):
    # MMD-Funktion F-1
    sinv = frappe.get_doc("Sales Invoice", sinv)
    sinv.ignore_pricing_rule = 1
    sinv.f1 = 1
    sinv.save()
    frappe.db.commit()
    if int(short) + int(long) > 0:
        round_qty_to_quarter(sinv.name, short, long)
    else:
        return

@frappe.whitelist()
def clear_free_pos(sinv, short=0, long=0):
    # MMD-Funktion F-5
    sinv = frappe.get_doc("Sales Invoice", sinv)
    
    items_to_remove = []
    for item in sinv.items:
        if item.rate == 0:
            items_to_remove.append(item)
        else:
            if frappe.db.exists("Item Price", {"price_list": sinv.customer, "price_list_rate": 0, "item_code": item.item_code}):
                items_to_remove.append(item)
    
    for item in items_to_remove:
        sinv.items.remove(item)
    
    sinv.f5 = 1
    sinv.save()
    frappe.db.commit()
    return

@frappe.whitelist()
def round_qty_to_quarter(sinv, short=0, long=0):
    # MMD-Funktion F-2
    sinv = frappe.get_doc("Sales Invoice", sinv)
    
    for item in sinv.items:
        if item.uom == 'Stunden':
            new_qty = float(math.ceil(item.qty * 4)) / 4
            item.qty = new_qty
    
    sinv.f2 = 1
    sinv.save()
    frappe.db.commit()
    if int(short) + int(long) > 0:
        contract_items_based_on_date(sinv.name, long)
    else:
        return

@frappe.whitelist()
def set_customer_price_list(sinv):
    # MMD-Funktion F-4
    sinv = frappe.get_doc("Sales Invoice", sinv)
    if frappe.db.exists("Price List", sinv.customer):
        sinv.selling_price_list = sinv.customer
    else:
        frappe.throw("Keine Kundenpreisliste mit dem Namen {0} gefunden!".format(sinv.customer))
        return
    
    for item in sinv.items:
        if frappe.db.exists("Item Price", {"price_list": sinv.customer, "item_code": item.item_code}):
            fetched_rate = frappe.db.get_value("Item Price", {"price_list": sinv.customer, "item_code": item.item_code}, ["price_list_rate"]) or 0
            item.rate = fetched_rate
            item.price_list_rate = fetched_rate
            if frappe.db.get_value("Item Price", {"price_list": sinv.customer, "item_code": item.item_code}, ["pauschalberechnung"]) == 1:
                item.uom = 'pro Durchgang Pauschal'
                item.qty = 1
    
    sinv.f4 = 1
    sinv.save()
    frappe.db.commit()
    if int(short) + int(long) > 0:
        clear_free_pos(sinv.name, short, long)
    else:
        return

@frappe.whitelist()
def contract_items_based_on_date(sinv, long=0):
    # MMD-Funktion F-3
    sinv = frappe.get_doc("Sales Invoice", sinv)
    
    # ergänzen mit fallback Datum wenn Datum fehlt
    last_date = sinv.posting_date.strftime("%d.%m.%Y")
    for item in sinv.items:
        # look for date
        clean_description = BeautifulSoup(item.description, "lxml").text
        if clean_description[2:3] == '.' and  clean_description[5:6] == '.':
            # mit Datum
            last_date = clean_description[:10]
        else:
            # setze fallback datum
            item.description = last_date + " " + clean_description
        item.datum = last_date.split(".")[2] + "-" + last_date.split(".")[1] + "-" + last_date.split(".")[0]
    
    # zusammenziehen wenn notwendig
    zusammenzug_verboten = []
    zusammenzug = {}
    for item in sinv.items:
        if frappe.db.exists("Item Price", {"price_list": sinv.customer, "item_code": item.item_code, "nicht_zusammenziehen": 1}):
            zusammenzug_verboten.append(str(item.name))
        else:
            clean_description = BeautifulSoup(item.description, "lxml").text
            item_date = clean_description[:10]
            item_key = str(item.item_code) + "/" + item_date
            if not item_key in zusammenzug:
                zusammenzug[item_key] = {}
                zusammenzug[item_key]['description'] = item.description
                zusammenzug[item_key]['qty'] = item.qty
            else:
                if zusammenzug[item_key]['description'].endswith("<br>"):
                    zusammenzug[item_key]['description'] = zusammenzug[item_key]['description'] + item.description
                else:
                    zusammenzug[item_key]['description'] = zusammenzug[item_key]['description'] + "<br>" + item.description
                zusammenzug[item_key]['qty'] = zusammenzug[item_key]['qty'] + item.qty
    
    zusammengezogene_items = []
    duplikat_kontrolle = []
    for item in sinv.items:
        if item.name in zusammenzug_verboten:
            zusammengezogene_items.append(item)
        else:
            clean_description = BeautifulSoup(item.description, "lxml").text
            item_date = clean_description[:10]
            item_key = str(item.item_code) + "/" + item_date
            if not item_key in duplikat_kontrolle:
                item.description = zusammenzug[item_key]['description']
                item.qty = zusammenzug[item_key]['qty']
                zusammengezogene_items.append(item)
                duplikat_kontrolle.append(item_key)
    
    sinv.items = []
    sinv.items = zusammengezogene_items
    
    # sort items by date
    for i, item in enumerate(sorted(sinv.items, key=lambda item: item.datum), start=1):
        item.idx = i
    
    sinv.f3 = 1
    sinv.save()
    frappe.db.commit()
    if int(long) > 0:
        set_customer_price_list(sinv.name)
    else:
        return

@frappe.whitelist()
def check_missing_price(idx, item_code, price_list="Standard-Vertrieb"):
    prices = frappe.db.get_list('Item Price',
                                filters={
                                    'item_code': item_code,
                                    'price_list': price_list
                                },
                                fields=['name', 'price_list_rate'])
    return {
        'price_list_rate': prices[0].price_list_rate if len(prices) > 0 else 0,
        'idx': idx
    }
