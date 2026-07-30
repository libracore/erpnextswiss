#!/usr/bin/env python3
"""Guard legacy ERPNextSwiss mutation endpoints against unsafe HTTP exposure."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "erpnextswiss"

REQUIRED_POST = {
    "assets.py:smart_scrap",
    "attach_pdf.py:attach_pdf",
    "customer_specific_extension.py:deactiviate_pricing_rule",
    "customer_specific_extension.py:clear_free_pos",
    "customer_specific_extension.py:round_qty_to_quarter",
    "customer_specific_extension.py:set_customer_price_list",
    "customer_specific_extension.py:contract_items_based_on_date",
    "dpd.py:transmit_to_dpd",
    "dynamic_newsletter.py:enqueue_send_dynamic_newsletter",
    "edi.py:check_create_desadv",
    "expenses.py:expense_pretax",
    "expenses.py:expense_pretax_various",
    "expenses.py:cancel_pretax",
    "finance.py:enqueue_build_long_fiscal_year_print",
    "finance.py:save_submit_close_payment_entry",
    "finance.py:deduct_and_close",
    "mautic.py:manual_sync_customer",
    "mautic.py:manual_sync_contact",
    "mautic.py:manual_sync_customer_with_contacts",
    "payrexx.py:create_payment",
    "planzer.py:create_shipment",
    "print_queue.py:print_doc_as_label",
    "print_queue.py:set_job_status",
    "scripts/asset_tools.py:unlink_asset",
    "scripts/crm_tools.py:update_contact_first_and_last_name",
    "scripts/crm_tools.py:change_customer_without_impact_on_price",
    "page/abacus_export/abacus_export.py:generate_transfer_file",
    "page/abacus_export/abacus_export.py:reset_export_flags",
    "page/bankimport/bankimport.py:parse_file",
    "page/bankimport/bankimport.py:parse_by_template",
    "page/bankimport/bankimport.py:read_camt053",
    "page/bankimport/bankimport.py:read_camt054",
    "page/bkp_importer/bkp_importer.py:read_xml",
    "page/bank_wizard/bank_wizard.py:read_camt053",
    "page/bank_wizard/bank_wizard.py:make_payment_entry",
    "page/bkp_importer/bkp_importer.py:import_update_items",
    "page/bkp_importer/utils.py:calc_structur_organisation_totals",
    "page/bkp_importer/utils.py:transfer_structur_organisation_discounts",
    "page/bkp_importer/utils.py:_transfer_structur_organisation_discounts",
    "page/bkp_importer/utils.py:make_sales_invoice",
    "page/bkp_importer/utils.py:check_for_changed_line_items",
    "page/bkp_importer/utils.py:set_amount_to_bill",
    "page/match_payments/match_payments.py:match",
    "page/match_payments/match_payments.py:submit",
    "page/match_payments/match_payments.py:submit_all",
    "page/match_payments/match_payments.py:auto_match",
    "page/payment_export/payment_export.py:generate_payment_file",
    "page/payment_export/payment_export.py:generate_payment_file_from_payroll",
    "report/service_invoicing/service_invoicing.py:create_invoice",
    "doctype/abacus_export_file/abacus_export_file.py:reset_export_flags",
    "doctype/direct_debit_proposal/direct_debit_proposal.py:create_bank_file",
    "doctype/direct_debit_proposal/direct_debit_proposal.py:create_direct_debit_proposal",
    "doctype/ebics_connection/ebics_connection.py:execute_payment",
    "doctype/gitlab_settings/gitlab_settings.py:create_new_issue",
    "doctype/gitlab_settings/gitlab_settings.py:edit_issue",
    "doctype/municipality/municipality.py:enqueue_import_municipality",
    "doctype/payment_proposal/payment_proposal.py:create_bank_file",
    "doctype/payment_proposal/payment_proposal.py:create_payment_proposal",
    "doctype/payment_proposal/payment_proposal.py:release_from_payment_proposal",
    "doctype/payment_reminder/payment_reminder.py:enqueue_create_payment_reminders",
    "doctype/payment_reminder/payment_reminder.py:create_payment_reminders",
    "doctype/payment_reminder/payment_reminder.py:create_reminder_for_customer",
    "doctype/payment_reminder/payment_reminder.py:bulk_submit",
    "doctype/pincode/pincode.py:enqueue_import_pincodes",
    "doctype/vat_declaration/vat_declaration.py:create_transfer_file",
    "doctype/zugferd_wizard/nextcloud_integration.py:fetch_invoice",
    "doctype/zugferd_wizard/testgen.py:create_supplier",
    "doctype/zugferd_wizard/zugferd_wizard.py:create_invoice",
    "doctype/zugferd_wizard/zugferd_wizard.py:manual_purchase_invoice",
    "doctype/zugferd_wizard/zugferd_wizard.py:fetch_invoice_from_nextcloud",
}

WRITE_CALLS = {
    "add_comment",
    "cancel",
    "commit",
    "db_set",
    "delete",
    "delete_doc",
    "enqueue",
    "enqueue_doc",
    "insert",
    "rename_doc",
    "save",
    "set_value",
    "submit",
}


def key_for(path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    relative = path.relative_to(PACKAGE_ROOT).as_posix()
    if relative.startswith("erpnextswiss/"):
        relative = relative.removeprefix("erpnextswiss/")
    return f"{relative}:{node.name}"


def decorator_text(source: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    return "\n".join(
        ast.get_source_segment(source, decorator) or ""
        for decorator in node.decorator_list
        if "whitelist" in (ast.get_source_segment(source, decorator) or "")
    )


def has_write_call(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        function = child.func
        name = (
            function.attr
            if isinstance(function, ast.Attribute)
            else function.id
            if isinstance(function, ast.Name)
            else ""
        )
        if name in WRITE_CALLS:
            return True
        if name == "sql" and child.args:
            sql = ast.unparse(child.args[0]).upper()
            if any(statement in sql for statement in ("UPDATE ", "INSERT ", "DELETE ")):
                return True
    return False


def function_source(path: Path, function_name: str) -> str:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Function not found: {path}:{function_name}")


def main() -> None:
    discovered_post: set[str] = set()
    unsafe_mutations: list[str] = []

    for path in PACKAGE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8-sig", errors="ignore")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise AssertionError(f"Cannot parse {path}: {exc}") from exc

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            whitelist = decorator_text(source, node)
            if not whitelist:
                continue
            key = key_for(path, node)
            if 'methods=["POST"]' in whitelist or "methods=['POST']" in whitelist:
                discovered_post.add(key)
            elif has_write_call(node):
                unsafe_mutations.append(key)

    missing = sorted(REQUIRED_POST - discovered_post)
    if missing:
        raise AssertionError(f"Mutation endpoints without POST protection: {missing}")
    if unsafe_mutations:
        raise AssertionError(f"Detected additional unsafe mutation endpoints: {unsafe_mutations}")

    crm_path = PACKAGE_ROOT / "scripts" / "crm_tools.py"
    customer_change = function_source(crm_path, "change_customer_without_impact_on_price")
    assert 'dt not in ("Quotation", "Sales Order")' in customer_change
    assert 'check_permission("write")' in customer_change
    assert "frappe.db.sql" not in customer_change
    assert "transaction.db_set(updates)" in customer_change

    contact_update = function_source(crm_path, "update_contact_first_and_last_name")
    assert 'check_permission("write")' in contact_update

    testgen = function_source(
        PACKAGE_ROOT / "erpnextswiss" / "doctype" / "zugferd_wizard" / "testgen.py",
        "create_supplier",
    )
    assert 'frappe.only_for("System Manager")' in testgen

    bkp_importer = PACKAGE_ROOT / "erpnextswiss" / "page" / "bkp_importer" / "bkp_importer.py"
    read_xml = function_source(bkp_importer, "read_xml")
    import_items = function_source(bkp_importer, "import_update_items")
    unzip_file = function_source(bkp_importer, "unzip_file")
    assert "_check_item_import_permission()" in read_xml
    assert "_uploaded_file_path(file_path)" in read_xml
    assert "_check_item_import_permission()" in import_items
    assert "extractall" not in unzip_file

    payment_reminders = (
        PACKAGE_ROOT
        / "erpnextswiss"
        / "doctype"
        / "payment_reminder"
        / "payment_reminder.py"
    )
    for function_name in ("create_payment_reminders", "create_reminder_for_customer"):
        reminder_function = function_source(payment_reminders, function_name)
        assert "_require_payment_reminder_access()" in reminder_function
        assert ".format(customer=" not in reminder_function
        assert ".format(company=" not in reminder_function

    payrexx = function_source(
        PACKAGE_ROOT / "erpnextswiss" / "payrexx.py",
        "create_payment",
    )
    assert "frappe.only_for" in payrexx

    planzer = function_source(
        PACKAGE_ROOT / "erpnextswiss" / "planzer.py",
        "create_shipment",
    )
    assert 'check_permission("write")' in planzer

    print(
        f"OK: {len(REQUIRED_POST)} mutation endpoints are POST-only; "
        "critical CRM writes are permission checked and SQL-safe."
    )


if __name__ == "__main__":
    main()
