# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# Part of this work is derived from pdf_on_submit, Copyright (C) 2019  Raffael Meyer <raffael@alyf.de>
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.core.doctype.file.file import create_new_folder
from frappe.utils.file_manager import save_file
import hashlib
import time
from frappe.utils import cint

@frappe.whitelist()
def attach_pdf(doctype, docname, event=None, print_format=None, hashname=None, is_private=1, background=1):
    fallback_language = frappe.db.get_single_value("System Settings", "language") or "en"
    args = {
        "doctype": doctype,
        "name": docname,
        "title": (frappe.get_value(doctype, docname, "title") or docname),
        "lang": (frappe.get_value(doctype, docname, "language") or fallback_language),
        "print_format": print_format,
        "hashname": cint(hashname),
        "is_private": cint(is_private)
    }

    if cint(background) == 1:
        enqueue(args)
    else:
        execute(**args)
    return

def enqueue(args):
    """Add method `execute` with given args to the queue."""
    frappe.enqueue(method=execute, queue='long',
                   timeout=90, is_async=True, **args)
    return

def execute(doctype, name, title, lang=None, print_format=None, hashname=None, is_private=1):
    if lang:
        frappe.local.lang = lang

    doctype_folder = create_folder(_(doctype), "Home")
    title_folder = create_folder(title, doctype_folder)

    pdf_data = get_pdf_data(doctype, name, print_format)

    save_and_attach(pdf_data, doctype, name, title_folder, hashname, is_private)
    return


def create_folder(folder, parent):
    """Make sure the folder exists and return it's name."""
    new_folder_name = "/".join([parent, folder])
    
    if not frappe.db.exists("File", new_folder_name):
        create_new_folder(folder, parent)
    
    return new_folder_name


def get_pdf_data(doctype, name, print_format=None):
    """Document -> HTML -> PDF."""
    html = frappe.get_print(doctype, name, print_format)
    return frappe.utils.pdf.get_pdf(html)


def save_and_attach(content, to_doctype, to_name, folder, hashname=None, is_private=1):
    """
    Save content to disk and create a File document.
    File document is linked to another document.
    """
    if not hashname:
        file_name = "{0}.pdf".format(to_name.replace(" ", "-").replace("/", "-"))
    else:
        # use a hased file name
        file_name = "{0}.pdf".format(hashlib.md5("{0}{1}".format(to_name, time.time()).encode('utf-8')).hexdigest())

    save_file(file_name, content, to_doctype,
              to_name, folder=folder, is_private=is_private)
    return
