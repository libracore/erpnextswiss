# -*- coding: utf-8 -*-
# Copyright (c) 2026, KT Waermesysteme and contributors

from __future__ import annotations

import json

import frappe
from frappe.translate import print_language
from frappe.www.printview import validate_print_permission


def _coerce_scalar(value):
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _normalize_none_like(value):
    value = _coerce_scalar(value)

    if value is None:
        return None

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"", "none", "null", "undefined"}:
            return None
        return value

    return value


def _normalize_no_letterhead(value):
    value = _coerce_scalar(value)
    if value is None:
        return 0

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"", "none", "null", "undefined"}:
            return 0
        if normalized in {"1", "true", "yes", "on"}:
            return 1
        if normalized in {"0", "false", "no", "off"}:
            return 0

    try:
        return 1 if int(value) else 0
    except (TypeError, ValueError):
        return 0


def _sanitize_print_language(value):
    normalized = _normalize_none_like(value)
    if normalized is None:
        return None
    return normalized


@frappe.whitelist(allow_guest=True)
def download_pdf(
    doctype,
    name,
    format=None,
    doc=None,
    no_letterhead=0,
    language=None,
    letterhead=None,
    pdf_generator=None,
    _lang=None,
    **kwargs,
):
    """Sanitize incoming query args for print downloads before delegating to get_print.

    This prevents broken links when callers send None-like string values (e.g.
    \"None\") for parameters such as no_letterhead.
    """

    del kwargs

    no_letterhead = _normalize_no_letterhead(no_letterhead)

    if language is None and _lang is not None:
        language = _lang

    language = _sanitize_print_language(language)
    letterhead = _normalize_none_like(letterhead)
    pdf_generator = _normalize_none_like(pdf_generator)

    if isinstance(doc, str):
        normalized_doc = _normalize_none_like(doc)
        if normalized_doc is None:
            doc = None
        else:
            try:
                doc = json.loads(normalized_doc)
            except (TypeError, ValueError):
                doc = normalized_doc

    permission_source = doc if hasattr(doc, "doctype") else frappe.get_doc(doctype, name)
    validate_print_permission(permission_source)

    print_kwargs = {
        "doc": doc,
        "as_pdf": True,
        "letterhead": letterhead,
        "no_letterhead": no_letterhead,
    }
    if pdf_generator is not None:
        print_kwargs["pdf_generator"] = pdf_generator

    with print_language(language):
        pdf_file = frappe.get_print(doctype, name, format, **print_kwargs)

    frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = pdf_file
    frappe.local.response.type = "pdf"
