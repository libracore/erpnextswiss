import re
import posixpath
import urllib.parse as urlparse
import requests
import xml.etree.ElementTree as ET
import io
from textwrap import dedent
import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.password import get_decrypted_password
from frappe.utils import cint

class NCSettings():
    def __init__(self):
        self.SETTINGS    = frappe.get_doc("NextCloud Settings", "NextCloud Settings")
        self.BASE_ORIGIN = self.SETTINGS.host
        self.USERNAME    = self.SETTINGS.user
        self.APP_PASS    = get_decrypted_password("NextCloud Settings", "NextCloud Settings", 'password', False)
        self.SRC_DIR     = self.SETTINGS.invoice_inbox
        self.DST_DIR     = self.SETTINGS.processed_invoices
        self.VERIFY_TLS  = True if cint(self.SETTINGS.verify_ssl) else False
        self.WEBDAV_BASE = f"{self.BASE_ORIGIN}/remote.php/dav/files/{urlparse.quote(self.USERNAME)}"
        self.PDF_RE      = re.compile(r"\.pdf$", re.IGNORECASE)
        self.ns          = {"d": "DAV:"}  # XML Namespace

def check_if_activ():
    # leave if nextcloud is not enabled
    if not cint(ncs.SETTINGS.enabled) or not cint(ncs.SETTINGS.enable_zugferd):
        frappe.msgprint(_("The ZUGFeRD <> NextCloud interface is disabled."))
        return False
    return True

def join_webdav_path(*parts: str) -> str:
    """Pfad korrekt als WebDAV-URL zusammensetzen (posix, ohne doppelte //)"""
    path = posixpath.join(*parts)
    # posixpath.join entfernt den führenden '/', der absolute Pfad relativ zu WEBDAV_BASE wird benötigt
    if not path.startswith("/"):
        path = "/" + path
    return ncs.WEBDAV_BASE + path

def propfind_list(folder_path: str):
    """Listet Einträge (Depth: 1) in einem Ordner via PROPFIND"""
    url = join_webdav_path(folder_path)
    headers = {
        "Depth": "1",
        "Content-Type": "application/xml; charset=utf-8"
    }
    body = dedent("""
        <?xml version="1.0" encoding="utf-8"?>
        <d:propfind xmlns:d="DAV:">
            <d:prop>
                <d:resourcetype/>
                <d:getcontenttype/>
                <d:getcontentlength/>
            </d:prop>
        </d:propfind>
    """).lstrip()
    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)
        r = s.request("PROPFIND", url, data=body, headers=headers, verify=ncs.VERIFY_TLS)
        r.raise_for_status()
        # XML parsen
        root = ET.fromstring(r.content)
        items = []
        for resp in root.findall("d:response", ncs.ns):
            href_el = resp.find("d:href", ncs.ns)
            if href_el is None:
                continue
            href = href_el.text  # z.B. /remote.php/dav/files/user/Eingang/datei.pdf

            # Eigenschaften auslesen
            prop = resp.find("d:propstat/d:prop", ncs.ns)
            if prop is None:
                continue
            is_collection = prop.find("d:resourcetype/d:collection", ncs.ns) is not None
            ctype = (prop.find("d:getcontenttype", ncs.ns).text or "") if prop.find("d:getcontenttype", ncs.ns) is not None else ""
            clen  = (prop.find("d:getcontentlength", ncs.ns).text or "") if prop.find("d:getcontentlength", ncs.ns) is not None else ""

            items.append({
                "href": href,
                "is_collection": is_collection,
                "content_type": ctype,
                "content_length": clen
            })
        return items


def ensure_folder(folder_path: str):
    """Erstellt Zielordner mit MKCOL, falls nicht vorhanden"""
    parts = [p for p in folder_path.split("/") if p]
    current = "/"
    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)
        for p in parts:
            current = posixpath.join(current, p)
            url = join_webdav_path(current)
            # Existenz per PROPFIND Depth:0 prüfen
            head = s.request("PROPFIND", url, headers={"Depth": "0"}, verify=ncs.VERIFY_TLS)
            if head.status_code == 404:
                mk = s.request("MKCOL", url, verify=ncs.VERIFY_TLS)
                if mk.status_code not in (201, 405):
                    # 201=created, 405=already exists (je nach Setup)
                    mk.raise_for_status()

def fetch_bytes(file_href: str) -> tuple[str, bytes]:
    url = ncs.BASE_ORIGIN + file_href if file_href.startswith("/") else file_href
    filename = urlparse.unquote(posixpath.basename(file_href))

    with requests.get(url, auth=(ncs.USERNAME, ncs.APP_PASS), stream=True, verify=ncs.VERIFY_TLS) as r:
        r.raise_for_status()
        buf = io.BytesIO()
        for chunk in r.iter_content(chunk_size=1024 * 128):
            if chunk:
                buf.write(chunk)
    
    return filename, buf.getvalue()


def move_file(src_href: str, dst_path_in_cloud: str):
    """
    Verschiebt Datei serverseitig via WebDAV MOVE
    src_href: HREF aus PROPFIND (z.B. /remote.php/dav/files/user/Eingang/a.pdf)
    dst_path_in_cloud: Zielpfad in Nextcloud (z.B. /Archiv/PDFs/a.pdf)
    """
    # Quell-URL
    src_url = ncs.BASE_ORIGIN + src_href if src_href.startswith("/") else src_href
    # Ziel-URL muss absolut sein und auf die DAV-Files-URL zeigen
    dst_url = join_webdav_path(dst_path_in_cloud)

    headers = {
        "Destination": dst_url,
        "Overwrite": "T"
    }
    with requests.Session() as s:
        s.auth = (ncs.USERNAME, ncs.APP_PASS)
        r = s.request("MOVE", src_url, headers=headers, verify=ncs.VERIFY_TLS)
        # 201 Created oder 204 No Content sind ok
        if r.status_code not in (201, 204):
            r.raise_for_status()

@frappe.whitelist()
def get_file_list():
    global ncs
    ncs = NCSettings()

    if not check_if_activ():
        return
    
    entries = propfind_list(ncs.SRC_DIR)

    # Erstes Element ist meistens der Ordner selbst, dieser wird weggefiltert (is_collection)
    files = [e for e in entries if not e["is_collection"]]

    pdfs = []
    for e in files:
        name = posixpath.basename(urlparse.unquote(e["href"]))
        if ncs.PDF_RE.search(name):
            pdfs.append(e)

    if not pdfs:
        msg = _("There are no invoices ready for collection in {SRC_DIR}.")
        frappe.msgprint(msg.format(SRC_DIR=ncs.SRC_DIR), "NextCloud")
        return

    pdf_list = []
    for e in pdfs:
        name = posixpath.basename(urlparse.unquote(e["href"]))
        filename = urlparse.unquote(posixpath.basename(e["href"]))
        pdf_list.append(f"""<li style="cursor: pointer;" class="invoice-fetch" data-invoice="{e["href"]}">{filename} <i class="fa fa-arrow-right"></i></li>""")
    
    msg = _("The following invoices were found in Nextcloud.<br>Click on them to process them.<br><br>")
    return f"""{msg}<ul style="list-style: none;padding-left: 0;">{''.join(pdf_list)}</ul>"""

@frappe.whitelist()
def fetch_invoice(invoice):
    global ncs
    ncs = NCSettings()

    # File von Nextcloud auslesen und in ERP speichern
    name = posixpath.basename(urlparse.unquote(invoice))
    filename, content = fetch_bytes(invoice)
    file_doc = save_file(
        fname=filename,
        content=content,
        dt="ZUGFeRD Wizard",
        dn="ZUGFeRD Wizard",
        df="file",
        is_private=1,
        folder="Home"
    )
    frappe.db.set_single_value("ZUGFeRD Wizard", "file", file_doc.file_url)

    # File in Nextcloud verschieben
    dst_cloud_path = posixpath.join(ncs.DST_DIR, name)
    move_file(invoice, dst_cloud_path)