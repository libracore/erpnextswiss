# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import hashlib
from bs4 import BeautifulSoup
import json
from datetime import datetime
import operator
import re
import six
from frappe.utils import get_site_name
import zipfile
from frappe.utils.background_jobs import enqueue, get_jobs
import os

@frappe.whitelist()
def read_xml(file_path, name):
    site_name = get_site_name(frappe.local.request.host)
    if site_name == 'localhost':
        site_name = 'site1.local'
    path_to_site_folder = '/home/frappe/frappe-bench/sites/' + site_name
    file = path_to_site_folder + file_path
    if ".zip" in file_path:
        path_to_file_folder = file.replace(file.split("/")[len(file.split("/")) - 1], "")
        name = unzip_file(path_to_file_folder, file)
        file = path_to_file_folder + name
    with open(file, "r") as f:
        contents = f.read()
        soup = BeautifulSoup(six.text_type(contents), 'xml')
        try:
            file = {
                'name': name,
                'katalog_daten': {
                    "ID_Anbieter": soup.DataExpert.Body.Katalog.get("ID_Anbieter"),
                    'ID_Katalog': soup.DataExpert.Body.Katalog.get("ID_Katalog"),
                    'Txt_Katalog': soup.DataExpert.Body.Katalog.get("Txt_Katalog"),
                    'Versions_Jahr': soup.DataExpert.Body.Katalog.get("Versions_Jahr"),
                    'Versions_Nr': soup.DataExpert.Body.Katalog.get("Versions_Nr"),
                    'Preisbuch_Nr': soup.DataExpert.Body.Katalog.get("Preisbuch_Nr"),
                    'Dat_Valid_Von': soup.DataExpert.Body.Katalog.get("Dat_Valid_Von"),
                    'Sprache': soup.DataExpert.Head.Code_Sprache.get_text()
                }
            }
        except:
            return 'Error'
        return file

@frappe.whitelist()
def import_update_items(xml_files):
    try:
        site_name = get_site_name(frappe.local.request.host)
        if site_name == 'localhost':
            site_name = 'site1.local'
        max_time = 7200
        args = {
            'xml_files': xml_files,
            'site_name': site_name
        }
        queue="long"
        queued_jobs = get_jobs(site=frappe.local.site, queue=queue)
        method = "erpnextswiss.erpnextswiss.page.bkp_importer.bkp_importer._import_update_items"
        job_name='Import / Update Items from BKP File(s)'
        if method not in queued_jobs[frappe.local.site]:
            frappe.msgprint(_("Der Import / Das Updaten wurde gestartet. Bitte warten Sie bis der Backgroundjob ausgeführt wurde.<br>Prüfen Sie im Anschluss den Errorlog auf allfällige Fehler."), 'Import / Update gestartet')
            enqueue(method=method, queue=queue, timeout=max_time, event=None, is_async=True, job_name=job_name, now=False, enqueue_after_commit=False, **args)
            return
        else:
            frappe.msgprint(_("Der Backup Job wurde bereits gestartet. Bitte warten Sie bis das System Ihnen mitteilt dass der Job erledigt ist."), 'Bitte Warten')
    except:
        return frappe.msgprint("Es ist etwas schief gelaufen.")

def _import_update_items(xml_files, site_name):
    new_created_items = 0
    updated_items = 0
    bkp_error = False
    xml_files = json.loads(xml_files)
    for xml_file in xml_files:
        file_name = xml_file
        file = '/home/frappe/frappe-bench/sites/' + site_name + '/private/files/' + file_name
        with open(file, "r") as f:
            contents = f.read()
            soup = BeautifulSoup(six.text_type(contents), 'xml')
            try:
                items = soup.DataExpert.Body.find_all('Artikel')
                item_group = soup.DataExpert.Head.Anbieter.Firma.get_text()
                if not frappe.db.exists('Item Group', item_group):
                    bkp_error = create_item_group(item_group)
            except Exception as e:
                bkp_error = True
                frappe.log_error("{0}".format(e), "BKP Importer: Lesen Artikel")
        if not bkp_error:
            for item in items:
                if not bkp_error:
                    if not frappe.db.exists('Item', item.get('Art_Nr_Anbieter')):
                        #create new item
                        bkp_error = create_new_item(item, soup, item_group)
                        new_created_items += 1
                    else:
                        #update item
                        bkp_error = update_item(item, soup, item_group)
                        updated_items += 1
            os.remove(file)
            files_from_home_bkp_uploads = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `folder` = 'Home/BKP-Uploads'""", as_list=True)
            if files_from_home_bkp_uploads:
                for file_to_delete in files_from_home_bkp_uploads:
                    frappe.db.sql("""DELETE FROM `tabFile` WHERE `name` = '{file_to_delete}'""".format(file_to_delete=file_to_delete[0]), as_list=True)

def create_new_item(item, soup, item_group):
    try:
        uom = item.BM_Einheit_Code.get('BM_Einheit')
    except:
        try:
            uom = item.Einheit_Code.get('Einheit')
        except:
            frappe.log_error("Einheit konnte nicht ausgelesen werden\n\n{0}".format(e), "BKP Importer: Erstellen Artikel")
            return True
    try:
        preis = item.Preis_Bestimmen.Preis.Preis_Pos.get_text()
    except:
        try:
            preis = item.Preis.get_text()
        except:
            frappe.log_error("Preis konnte nicht ausgelesen werden\n\n{0}".format(e), "BKP Importer: Erstellen Artikel")
            return True
    try:
        new_item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item.get('Art_Nr_Anbieter'),
            "item_name": item.Art_Txt_Kurz.get_text(),
            "description": item.Art_Txt_Lang.get_text(),
            "uom": uom,
            "item_group": item_group,
            "is_stock_item": 0,
            "include_item_in_manufacturing": 0
        })
        new_item.insert()
        frappe.db.commit()
        bkp_error = create_item_price(new_item.name, preis)
        if not bkp_error:
            return False
        else:
            return True
    except Exception as e:
        frappe.log_error("{0}".format(e), "BKP Importer: Erstellen Artikel")
        return True

def update_item(_item, soup, item_group):
    try:
        uom = _item.BM_Einheit_Code.get('BM_Einheit')
    except:
        try:
            uom = _item.Einheit_Code.get('Einheit')
        except:
            frappe.log_error("Einheit konnte nicht ausgelesen werden\n\n{0}".format(e), "BKP Importer: Updaten Artikel")
            return True
    try:
        preis = _item.Preis_Bestimmen.Preis.Preis_Pos.get_text()
    except:
        try:
            preis = _item.Preis.get_text()
        except:
            frappe.log_error("Preis konnte nicht ausgelesen werden\n\n{0}".format(e), "BKP Importer: Updaten Artikel")
            return True
    try:
        item = frappe.get_doc("Item", _item.get('Art_Nr_Anbieter'))
        item.item_name = _item.Art_Txt_Kurz.get_text()
        item.description = _item.Art_Txt_Lang.get_text()
        item.uom = uom
        item.item_group = item_group
        item.save()
        frappe.db.commit()
        bkp_error = update_item_price(item.name, preis)
        if not bkp_error:
            return False
        else:
            return True
    except Exception as e:
        frappe.log_error("{0}".format(e), "BKP Importer: Updaten Artikel")
        return True

def create_item_group(item_group):
    try:
        default_item_group = frappe.db.get_single_value('Stock Settings', 'item_group')
        new_item_group = frappe.get_doc({
            "doctype": "Item Group",
            "parent_item_group": default_item_group,
            "item_group_name": item_group
        })
        new_item_group.insert()
        frappe.db.commit()
        return False
    except Exception as e:
        frappe.log_error("{0}".format(e), "BKP Importer: Erstellen Artikelgruppe")
        return True

def create_item_price(item, price):
    try:
        default_price_list = frappe.db.sql("""SELECT `name` FROM `tabPrice List` WHERE `selling` = 1""", as_list=True)[0][0]
        new_item_price = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item,
            "price_list": default_price_list,
            "selling": 1,
            "buying": 0,
            "price_list_rate": price
        })
        new_item_price.insert()
        frappe.db.commit()
        return False
    except Exception as e:
        frappe.log_error("{0}".format(e), "BKP Importer: Erstellen Artikelpreis")
        return True

def update_item_price(item, price):
    try:
        default_price_list = frappe.db.sql("""SELECT `name` FROM `tabPrice List` WHERE `selling` = 1""", as_list=True)[0][0]
        price_lists = frappe.db.sql("""SELECT `name` FROM `tabItem Price` WHERE `item_code` = '{item}' AND `price_list` = '{default_price_list}' AND `selling` = 1""".format(item=item, default_price_list=default_price_list), as_list=True)
        try:
            _price_list = price_lists[0][0]
            price_list = frappe.get_doc("Item Price", _price_list)
            price_list.price_list_rate = price
            price_list.save()
            frappe.db.commit()
            return False
        except:
            return create_item_price(item, price)
    
    except Exception as e:
        frappe.log_error("{0}".format(e), "BKP Importer: Update Artikelpreis")
        return True

def unzip_file(path_to_file_folder, file):
    with zipfile.ZipFile(file,"r") as zip_ref:
        zip_ref.extractall(path_to_file_folder)
        name_to_return = zip_ref.namelist()[0]
    os.remove(file)
    return name_to_return
