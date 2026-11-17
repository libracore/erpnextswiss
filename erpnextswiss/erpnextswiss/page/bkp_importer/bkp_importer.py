# Copyright (c) 2017-2026, libracore and contributors
# License: AGPL v3. See LICENCE

import json
import zipfile
from html import escape

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils.background_jobs import enqueue, get_jobs


def _get_upload(file_path):
    filters = {"file_url": file_path} if file_path.startswith("/") else {"file_name": file_path}
    name = frappe.db.get_value("File", filters, "name")
    if not name:
        frappe.throw(_("Die Upload-Datei wurde nicht gefunden: {0}").format(file_path))
    
    upload = frappe.get_doc("File", name)
    upload.check_permission("read")

    return upload


def _read_catalog(upload):
    path = upload.get_full_path()
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            members = [entry for entry in archive.infolist() if not entry.is_dir() and entry.filename.lower().endswith(".xml")]
            if len(members) != 1:
                frappe.throw(_("Die ZIP-Datei muss genau eine XML-Datei enthalten."))
            contents = archive.read(members[0])
    else:
        with open(path, "rb") as stream:
            contents = stream.read()
    
    return BeautifulSoup(contents, "xml")


@frappe.whitelist()
def read_xml(file_path, name):
    upload = _get_upload(file_path)
    soup = _read_catalog(upload)
    try:
        catalog = soup.DataExpert.Body.Katalog
        data = {key: catalog.get(key) for key in ( "ID_Anbieter", "ID_Katalog", "Txt_Katalog", "Versions_Jahr", "Versions_Nr", "Preisbuch_Nr", "Dat_Valid_Von")}
        data["Sprache"] = soup.DataExpert.Head.Code_Sprache.get_text()
    except AttributeError:
        frappe.throw(_("Die Datei enthält keinen gültigen DataExpert-Katalog."))
    
    return {
        "name": upload.file_url,
        "katalog_daten": data
    }


def _result_cache_key():
    return "bkp_import_result:" + frappe.session.user


@frappe.whitelist()
def get_import_status():
    return frappe.cache.get_value(_result_cache_key())


@frappe.whitelist()
def dismiss_import_result():
    key = _result_cache_key()
    result = frappe.cache.get_value(key)
    if result and result.get("status") == "completed":
        frappe.cache.delete_value(key)
        return True
    
    return False


@frappe.whitelist()
def import_update_items(xml_files):
    files = json.loads(xml_files) if isinstance(xml_files, str) else xml_files
    if not isinstance(files, list) or not files:
        frappe.throw(_("Bitte mindestens eine Datei auswählen."))
    
    for file_path in files:
        _get_upload(file_path)
    
    queue = "long"
    method = "erpnextswiss.erpnextswiss.page.bkp_importer.bkp_importer._import_update_items"
    if method in get_jobs(site=frappe.local.site, queue=queue)[frappe.local.site]:
        frappe.msgprint(_("Der Import läuft bereits. Bitte warten Sie auf den Abschluss."))
        return False
    
    frappe.cache.set_value(_result_cache_key(), {"status": "running"}, expires_in_sec=604800)
    try:
        enqueue(method=method, queue=queue, timeout=7200, xml_files=files,
                site_name=frappe.local.site)
    except Exception:
        frappe.cache.delete_value(_result_cache_key())
        raise

    frappe.msgprint(_("Der Import wurde gestartet. Nach der Verarbeitung erhalten Sie eine Zusammenfassung."))
    return True


def _import_update_items(xml_files, site_name):
    files = json.loads(xml_files) if isinstance(xml_files, str) else xml_files
    result = {"created": 0, "updated": 0, "errors": []}
    for file_path in files:
        try:
            upload = _get_upload(file_path)
            soup = _read_catalog(upload)
            items = soup.DataExpert.Body.find_all("Artikel")
            item_group = soup.DataExpert.Head.Anbieter.Firma.get_text()
            catalog = soup.DataExpert.Body.Katalog
            version = catalog.get("Versions_Jahr") + "/" + catalog.get("Versions_Nr")
            if not frappe.db.exists("Item Group", item_group):
                create_item_group(item_group, version)
            else:
                frappe.db.set_value("Item Group", item_group, "bkp_katalog_version", version)
            frappe.db.commit()
        except Exception as exc:
            frappe.db.rollback()
            result["errors"].append({"file": file_path, "item": "–", "error": str(exc)})
            continue

        for item in items:
            code = item.get("Art_Nr_Anbieter")
            frappe.db.savepoint("bkp_article")
            try:
                if not code:
                    raise ValueError("Artikelnummer fehlt.")
                exists = frappe.db.exists("Item", code)
                if exists:
                    update_item(item, soup, item_group)
                else:
                    create_new_item(item, soup, item_group)
            except Exception as exc:
                frappe.db.rollback(save_point="bkp_article")
                result["errors"].append({"file": file_path, "item": code or "–", "error": str(exc)})
            else:
                frappe.db.commit()
                result["updated" if exists else "created"] += 1
    
    _report_result(result)

    return result


def _report_result(result):
    summary = "Neu erstellt: {created} | Aktualisiert: {updated} | Fehler: {count}".format(count=len(result["errors"]), **result)
    message = "<p>" + summary + "</p>"
    if result["errors"]:
        rows = "".join("<tr>" + "".join("<td>" + escape(str(error[key])) + "</td>"
                       for key in ("file", "item", "error")) + "</tr>"
                       for error in result["errors"])
        message += ("<div style='max-height:60vh;overflow:auto'><table class='table table-bordered'>"
                    "<thead><tr><th>Datei</th><th>Artikel</th><th>Fehler</th></tr></thead>"
                    "<tbody>" + rows + "</tbody></table></div>")
        
        frappe.log_error(title="BKP Import: Zusammenfassung", message=summary + "\n\n" + json.dumps(result["errors"], ensure_ascii=False, indent=2))
        frappe.db.commit()
    
    frappe.cache.set_value(_result_cache_key(), {"status": "completed", "message": message}, expires_in_sec=604800)


def _item_values(item):
    unit = item.BM_Einheit_Code or item.Einheit_Code
    if unit is None:
        raise ValueError("Einheit fehlt.")
    
    uom = unit.get("BM_Einheit") or unit.get("Einheit")
    if not uom:
        raise ValueError("Einheit fehlt.")
    
    price = item.select_one("Preis_Bestimmen > Preis > Preis_Pos")
    if price is None:
        price = item.Preis
    if price is None:
        raise ValueError("Preis fehlt.")
    
    if item.Art_Txt_Kurz is None or item.Art_Txt_Lang is None:
        raise ValueError("Artikeltext fehlt.")
    
    return uom, price.get_text()


def create_new_item(item, soup, item_group):
    uom, price = _item_values(item)
    doc = frappe.get_doc({
        "doctype": "Item",
        "item_code": item.get("Art_Nr_Anbieter"),
        "item_name": item.Art_Txt_Kurz.get_text(),
        "description": item.Art_Txt_Lang.get_text(),
        "stock_uom": uom,
        "item_group": item_group,
        "is_stock_item": 0,
        "include_item_in_manufacturing": 0,
    })
    doc.insert()

    create_item_price(doc.name, price)
    return False


def update_item(_item, soup, item_group):
    uom, price = _item_values(_item)
    doc = frappe.get_doc("Item", _item.get("Art_Nr_Anbieter"))
    doc.item_name = _item.Art_Txt_Kurz.get_text()
    doc.description = _item.Art_Txt_Lang.get_text()
    doc.stock_uom = uom
    doc.item_group = item_group
    doc.save()
    update_item_price(doc.name, price)
    return False


def create_item_group(item_group, bkp_katalog_version):
    frappe.get_doc({
        "doctype": "Item Group",
        "parent_item_group": frappe.db.get_single_value("Stock Settings", "item_group"),
        "item_group_name": item_group, "bkp_katalog_version": bkp_katalog_version
    }).insert()
    return False


def _selling_price_list():
    name = frappe.db.get_value("Price List", {"selling": 1}, "name")
    if not name:
        raise ValueError("Keine Verkaufspreisliste vorhanden.")
    
    return name


def create_item_price(item, price):
    frappe.get_doc({
        "doctype": "Item Price",
        "item_code": item,
        "price_list": _selling_price_list(),
        "selling": 1,
        "buying": 0,
        "price_list_rate": price
    }).insert()
    return False


def update_item_price(item, price):
    name = frappe.db.get_value("Item Price", {"item_code": item, "price_list": _selling_price_list(), "selling": 1}, "name")
    if name:
        doc = frappe.get_doc("Item Price", name)
        doc.price_list_rate = price
        doc.save()
    else:
        create_item_price(item, price)
    
    return False
