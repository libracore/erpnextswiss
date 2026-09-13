# Existing Bank Wizard: account-bound matching

The banking goal reuses reconciliation and payment proposals. This change
hardens reads in the existing `bank_wizard.read_camt_transactions` engine; it
does not introduce different matching rules or an automatic booking workflow.

## Corrected source observations

- Several invoice and HR candidate queries used unrestricted get_all without
  company filters. The no-TxDtls payment-duplicate branch was not company-bound.
- Existing payment lookups did not consistently bind the selected bank account
  and included cancelled entries. An unrelated payment could hide an incoming row.
- Child proposal rows were searched by a bank-supplied parent reference without
  checking the parent company's scope/permissions first.
- `read_camt053` selected the first global IBAN hit, replacing the selected
  account and potentially its company. A no-match flag could remove company
  filtering altogether.
- A nominal read could write Error Logs, including for each matching pattern.

## Existing entry points retained

The existing public `read_camt053` path still returns transactions/html/bank and
uses the same rendering function. It now checks the explicit bank account and
company read permissions before parsing and never silently switches account.
When the file contains an IBAN, it must match the selected account. Existing
manual account-number-only input remains manual; it is not a trusted gateway
binding. Invalid/disabled/group accounts and permission failures are rejected.

The matching engine constructs `BankMatchingScope` and keeps its prior mapping
rules/output fields. Candidate reads use native permission-filtered get_list.
Invoices, HR records and payments remain in the selected company. Existing payment
duplicates must touch the selected account on paid_from or paid_to and must not
be cancelled. Child proposal access first resolves the exact permitted parent in
that company. A matching reference never grants access by itself.

Customer/Supplier remain shared-party DocTypes, subject to native permissions.
Optional unavailable/inaccessible HR candidates are omitted without preventing
other bank matching. Pattern configuration remains consumable by Accounts Users
without granting editor access to the Accounts-Manager-only configuration screen.
It is configuration, not an unrestricted financial-record query.

The compatibility argument skip_company_filter remains accepted but cannot
disable company/account isolation. Security boundaries are not an optional mode.
A new keyword-only read_only=True suppresses database Error Log writes, including
debug/pattern diagnostics. It does not create/submit payments or commit. This is
the call mode for the future bank transport preview, not a new public endpoint.

## Verification and remaining boundaries

Eight isolated tests cover scope construction, roles/account/company checks,
filters/immutability, both payment account directions, cancelled rows, proposal
parent gates and missing/inaccessible optional HR. They pass together with all
27 previous isolated tests. Native tests additionally exercise actual Frappe
queries/User Permissions with synthetic records and the actual existing matcher,
including both TxDtls branches, same IBAN across companies, unchanged return
shape, pattern matching and denied insert/save/submit/commit/log operations.
These new native tests must pass for the eventual commit before claiming that
native regression gate. CI runs them in the full app and again with HRMS present.

This is not the final bank-to-ERP handover. Gateway configuration/keys/mTLS,
the validated archive's namespace/multi-statement/054 adapter, existing
ebics_statement import writes and lifecycle, reliable statement identity and
053/054 overlap, permissions across all gateway surfaces, restore, approved
pilot and controlled deploy remain release gates. No bank action or production
financial/source update is authorized or performed by this change.
All original 14 platform packages remain part of the goal.
