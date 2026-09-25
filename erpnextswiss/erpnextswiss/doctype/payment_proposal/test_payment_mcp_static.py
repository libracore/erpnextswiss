# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PAYMENT_PROPOSAL = ROOT / "erpnextswiss" / "erpnextswiss" / "doctype" / "payment_proposal" / "payment_proposal.py"
PAYMENT_EXPORT = ROOT / "erpnextswiss" / "erpnextswiss" / "page" / "payment_export" / "payment_export.py"


def _source(path):
    return path.read_text(encoding="utf-8")


def _function_source(path, name):
    source = _source(path)
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node)
    raise AssertionError("function not found: {0}".format(name))


def _whitelist_decorator_source(path, name):
    source = _source(path)
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return "\n".join(
                ast.get_source_segment(source, decorator) or ""
                for decorator in node.decorator_list
                if "whitelist" in (ast.get_source_segment(source, decorator) or "")
            )
    raise AssertionError("function not found: {0}".format(name))


def test_payment_proposal_mcp_mutations_are_post_only():
    for name in (
        "create_payment_proposal_for_mcp",
        "cancel_payment_proposal_for_mcp",
        "create_payment_proposal_bank_file_for_mcp",
        "set_supplier_payment_details_for_mcp",
    ):
        assert 'methods=["POST"]' in _whitelist_decorator_source(PAYMENT_PROPOSAL, name)

    assert 'methods=["POST"]' in _whitelist_decorator_source(PAYMENT_EXPORT, "generate_payment_file_for_mcp")


def test_payment_proposal_mcp_mutations_keep_role_and_confirmation_guards():
    guarded = (
        (PAYMENT_PROPOSAL, "create_payment_proposal_for_mcp"),
        (PAYMENT_PROPOSAL, "cancel_payment_proposal_for_mcp"),
        (PAYMENT_PROPOSAL, "create_payment_proposal_bank_file_for_mcp"),
        (PAYMENT_PROPOSAL, "set_supplier_payment_details_for_mcp"),
        (PAYMENT_EXPORT, "generate_payment_file_for_mcp"),
    )
    for path, name in guarded:
        source = _function_source(path, name)
        assert 'frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))' in source

    for name in (
        "cancel_payment_proposal_for_mcp",
        "create_payment_proposal_bank_file_for_mcp",
        "set_supplier_payment_details_for_mcp",
    ):
        assert "_require_confirmed(confirm" in _function_source(PAYMENT_PROPOSAL, name)
    assert "_require_confirmed(confirm" in _function_source(PAYMENT_EXPORT, "generate_payment_file_for_mcp")
    create_source = _function_source(PAYMENT_PROPOSAL, "create_payment_proposal_for_mcp")
    assert "submit_now = _truthy(submit)" in create_source
    assert "if submit_now:" in create_source


def test_payment_proposal_mcp_defaults_exclude_salary_slips():
    source = _function_source(PAYMENT_PROPOSAL, "create_payment_proposal_for_mcp")
    assert "include_salary_slips=0" in source


def test_list_view_payment_proposal_stays_backward_compatible():
    source = _function_source(PAYMENT_PROPOSAL, "create_payment_proposal")
    assert "_create_payment_proposal_record" in source
    assert "include_salary_slips=None" in source
    assert 'return get_url_to_form("Payment Proposal", proposal_record.name)' in source
