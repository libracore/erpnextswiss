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
from frappe.utils.background_jobs import enqueue
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
		max_time = 4800
		kwargs = {
			'xml_files': xml_files,
			'site_name': site_name
		}
		frappe.publish_realtime(event='msgprint', message={'message': "Der Import / Das Updaten wurde gestartet. Bitte warten Sie bis das System mitteilt, dass der Auftrag ausgeführt wurde."}, user=frappe.session.user)
		enqueue(method="erpnextswiss.erpnextswiss.page.bkp_importer.bkp_importer._import_update_items", queue='long', job_name='Import / Update Items from BKP File(s)', timeout=max_time, **kwargs)
		return
	except:
		return 'Error'

def _import_update_items(xml_files, site_name):
	new_created_items = 0
	updated_items = 0
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
					create_item_group(item_group)
			except:
				return 'Error'
		for item in items:
			if not frappe.db.exists('Item', item.get('Art_Nr_Anbieter')):
				#create new item
				create_new_item(item, soup, item_group)
				new_created_items += 1
			else:
				#update item
				update_item(item, soup, item_group)
				updated_items += 1
		os.remove(file)
		files_from_home_bkp_uploads = frappe.db.sql("""SELECT `name` FROM `tabFile` WHERE `folder` = 'Home/BKP-Uploads'""", as_list=True)
		if files_from_home_bkp_uploads:
			for file_to_delete in files_from_home_bkp_uploads:
				frappe.db.sql("""DELETE FROM `tabFile` WHERE `name` = '{file_to_delete}'""".format(file_to_delete=file_to_delete[0]), as_list=True)
				
	frappe.publish_realtime(event='msgprint', message={'message': "Es wurden erfolgreich {new_created_items} Artikel angelegt und {updated_items} updated".format(new_created_items=new_created_items, updated_items=updated_items)}, user=frappe.session.user)
	return {
			'created': new_created_items,
			'updated': updated_items
		}
		
def create_new_item(item, soup, item_group):
	new_item = frappe.get_doc({
		"doctype": "Item",
		"item_code": item.get('Art_Nr_Anbieter'),
		"item_name": item.Art_Txt_Kurz.get_text(),
		"description": item.Art_Txt_Lang.get_text(),
		"uom": item.BM_Einheit_Code.get('BM_Einheit'),
		"item_group": item_group
	})
	new_item.insert()
	frappe.db.commit()
	create_item_price(new_item.name, item.Preis_Bestimmen.Preis.Preis_Pos.get_text())
	return

def update_item(_item, soup, item_group):
	item = frappe.get_doc("Item", _item.get('Art_Nr_Anbieter'))
	item.item_name = _item.Art_Txt_Kurz.get_text()
	item.description = _item.Art_Txt_Lang.get_text()
	item.uom = _item.BM_Einheit_Code.get('BM_Einheit')
	item.item_group = item_group
	item.save()
	frappe.db.commit()
	update_item_price(item.name, _item.Preis_Bestimmen.Preis.Preis_Pos.get_text())
	return
	
def create_item_group(item_group):
	new_item_group = frappe.get_doc({
		"doctype": "Item Group",
		"parent_item_group": _("All Item Groups"),
		"item_group_name": item_group
	})
	new_item_group.insert()
	frappe.db.commit()
	return
	
def create_item_price(item, price):
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
	return
	
def update_item_price(item, price):
	default_price_list = frappe.db.sql("""SELECT `name` FROM `tabPrice List` WHERE `selling` = 1""", as_list=True)[0][0]
	price_lists = frappe.db.sql("""SELECT `name` FROM `tabItem Price` WHERE `item_code` = '{item}' AND `price_list` = '{default_price_list}' AND `selling` = 1""".format(item=item, default_price_list=default_price_list), as_list=True)
	try:
		_price_list = price_lists[0][0]
		price_list = frappe.get_doc("Item Price", _price_list)
		price_list.price_list_rate = price
		price_list.save()
		frappe.db.commit()
	except:
		create_item_price(item, price)
	return
	
def unzip_file(path_to_file_folder, file):
	with zipfile.ZipFile(file,"r") as zip_ref:
		zip_ref.extractall(path_to_file_folder)
		name_to_return = zip_ref.namelist()[0]
	os.remove(file)
	return name_to_return