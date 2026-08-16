# -*- coding: utf-8 -*-
#
# item_tools.py
#
# Copyright (C) libracore, 2017-2024
# https://www.libracore.com or https://github.com/libracore
#
# Execute with $ bench execute erpnextswiss.scripts.item_tools.<function>
#

from __future__ import unicode_literals

import re

import frappe

# Regular expressions for supplier hint lines in Item descriptions.
SUPPLIER_HINT_PATTERNS = (
    re.compile(r"^\s*(?:lieferant|supplier)\s*[:\-]?\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*(?:lieferanten?nr\.?|liefernummer|supplier.?number|supplier.?no\.?)\s*[:\-]?\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*(?:eigener\s+lieferant|unserer\s+lieferant|unsere\s+lieferanten?)\s*[:\-]?\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*(?:bezug|bezugsquelle|quelle)\s+von\s*[:\-]?\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*(?:hersteller|manufacturer)\s*[:\-]?\s*.*$", re.IGNORECASE),
)


def _line_has_supplier_hint(line):
    normalized_line = re.sub(r"<[^>]+>", "", line or "").strip().lower()
    if not normalized_line:
        return False
    return any(pattern.match(normalized_line) for pattern in SUPPLIER_HINT_PATTERNS)


def _clean_item_description(description):
    if not description:
        return description

    separator_pattern = re.compile(r"<br\s*/?>|\r\n|\r|\n", re.IGNORECASE)
    raw_lines = separator_pattern.split(description)
    cleaned_lines = []

    for line in raw_lines:
        if _line_has_supplier_hint(line):
            continue
        cleaned_line = re.sub(r"\s+$", "", line or "").strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    return "<br>".join(cleaned_lines)


def _normalize_for_compare(value):
    if value is None:
        return ""
    return re.sub(
        r"\s*<br\s*/?>\s*",
        "<br>",
        re.sub(r"\s+", "", value.strip().lower())
    )


@frappe.whitelist()
def get_next_item_code():
    prefix = None
    last_item_code = frappe.db.sql(
        """SELECT `name` FROM `tabItem` ORDER BY CAST(`name` AS int) DESC LIMIT 1""",
        as_dict=True
    )
    # Check if already an item exist
    if last_item_code:
        last_item_code = str(last_item_code[0].name)
        last_item_code_len = len(last_item_code.split("-"))
        if last_item_code_len > 1:
            last_item_code = last_item_code.split("-")[last_item_code_len - 1]
            prefix = last_item_code.replace(last_item_code.split("-")[last_item_code_len - 1], "")
            new_item_code = int(last_item_code) + 1
            new_item_code = prefix + str(new_item_code)
        else:
            new_item_code = int(last_item_code) + 1
        return new_item_code
    else:
        return 1


@frappe.whitelist()
def purge_supplier_hints_from_item_descriptions(apply=0, item_codes=None, limit=None):
    """
    Remove supplier hint lines from Item description fields.

    Args:
      apply (bool/int): 0 = dry-run, 1 = write changes
      item_codes (str/list): optional item code filter (comma-separated string or list)
      limit (int): optional maximum number of items to process
    """
    apply = int(apply)

    filters = {"disabled": 0}
    if item_codes:
        if isinstance(item_codes, str):
            item_codes = [c.strip() for c in item_codes.split(",") if c.strip()]
        elif not isinstance(item_codes, list):
            item_codes = [item_codes]
        if item_codes:
            filters["name"] = ["in", item_codes]

    fields = ["name", "description", "web_long_description"]
    items = frappe.get_all("Item", filters=filters, fields=fields, limit=limit)

    preview = []
    changed = 0
    checked = 0

    for item in items:
        checked += 1
        changes = {}

        old_description = item.get("description")
        old_web_description = item.get("web_long_description")

        new_description = _clean_item_description(old_description)
        new_web_description = _clean_item_description(old_web_description)

        if _normalize_for_compare(old_description) != _normalize_for_compare(new_description):
            changes["description"] = {"before": old_description, "after": new_description}

        if _normalize_for_compare(old_web_description) != _normalize_for_compare(new_web_description):
            changes["web_long_description"] = {"before": old_web_description, "after": new_web_description}

        if not changes:
            continue

        changed += 1
        if len(preview) < 20:
            preview.append({"item": item.get("name"), "changes": changes})

        if apply:
            doc = frappe.get_doc("Item", item.get("name"))
            if "description" in changes:
                doc.description = new_description
            if "web_long_description" in changes:
                doc.web_long_description = new_web_description
            doc.save(ignore_permissions=True)
            frappe.db.commit()

    return {
        "applied": bool(apply),
        "checked": checked,
        "changed": changed,
        "preview": preview
    }


@frappe.whitelist()
def get_voucher_value(voucher_code, customer):
    sql_query = u"""SELECT
                    (IFNULL(SUM(`qty` * `base_rate`), 0)) AS `value`
                FROM `tabSales Invoice Item`
                WHERE
                    `item_code` = '{voucher}'
                    AND `parent` IN (SELECT `name` FROM `tabSales Invoice` WHERE `docstatus` = 1 AND `customer` = '{customer}');""".format(voucher=voucher_code, customer=customer)
    value = frappe.db.sql(sql_query, as_dict=True)
    if value:
        return { 'value': value[0].value }
    else:
        return { 'value': 0 }
