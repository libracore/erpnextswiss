# MCP Payment Workflow Endpoints

These whitelisted methods expose the payment workflow through controlled Frappe
method calls. They are intentionally narrow: no generic document writes, no raw
SQL access, and payment-impacting actions require explicit confirmation plus
optional expected totals/counts.

## Supplier Payment Details

Method:

```text
erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.set_supplier_payment_details_for_mcp
```

Use for adding or correcting supplier IBAN/BIC/default payment method.

Required safeguards:

```json
{
  "supplier": "Supplier Name",
  "default_payment_method": "IBAN",
  "iban": "CH2808387000001080802",
  "bic": "BBRUCHGT",
  "confirm": 1,
  "reason": "MCP payment preparation"
}
```

## Payment Proposal

Method:

```text
erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.create_payment_proposal_for_mcp
```

By default this endpoint excludes salary slips. Set `include_salary_slips=1`
only when submitted Salary Slips should be part of the proposal.

Recommended payload for supplier invoices only:

```json
{
  "date": "2026-09-15",
  "company": "KT Waermesysteme AG",
  "currency": "CHF",
  "pay_from_account": "1020 - Bankguthaben (inkl. PostFinance) (Bank) - KT-Waerme",
  "title": "2026-08-29 bis 2026-09-15 ohne Lohn",
  "include_expense_claims": 1,
  "include_salary_slips": 0,
  "submit": 1,
  "confirm": 1,
  "expected_total": 1685.9,
  "expected_purchase_invoice_count": 2,
  "reason": "Payment proposal for due invoices"
}
```

The method returns a structured summary with proposal name, URL, totals, counts,
selected Purchase Invoices, expenses, salary slips and generated payment rows.

## Cancel Payment Proposal

Method:

```text
erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.cancel_payment_proposal_for_mcp
```

Recommended safeguards:

```json
{
  "payment_proposal": "a7vkr4o278",
  "expected_total": 1685.9,
  "expected_payment_count": 2,
  "confirm": 1,
  "reason": "Replace incorrect payment proposal"
}
```

## Payment Proposal Bank File

Method:

```text
erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.create_payment_proposal_bank_file_for_mcp
```

This returns the pain.001 XML content, filename and message id. It does not
send the file to the bank.

```json
{
  "payment_proposal": "a7vkr4o278",
  "expected_total": 1685.9,
  "expected_payment_count": 2,
  "confirm": 1,
  "reason": "Create online banking upload file"
}
```

## Existing Payment Entry Export

Method:

```text
erpnextswiss.erpnextswiss.page.payment_export.payment_export.generate_payment_file_for_mcp
```

Use for already drafted Payment Entries. This validates the full selection
before delegating to the existing export, which submits included Payment Entries.

```json
{
  "payments": ["ACC-PAY-2026-00001", "ACC-PAY-2026-00002"],
  "expected_total": 1747.5,
  "expected_count": 2,
  "confirm": 1,
  "reason": "Export selected draft payment entries"
}
```

## Not Covered Here

Bank statement reconciliation, accounting completeness checks and end-to-end
closing controls remain separate workflows. They should get their own read/check
and narrowly confirmed mutation endpoints instead of being folded into payment
proposal creation.
