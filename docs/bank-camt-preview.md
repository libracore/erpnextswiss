# camt archive handover to the existing Bank Wizard

This is a read-only integration stage in ERPNextSwiss, not a second parser for
invoice matching, a payment proposal workflow, or a production bank connection.
`preview_camt_archive` is internal and deliberately not whitelisted. It does not
fetch bank data, persist imports, create payments, render HTML, or book entries.

## Entry point and source binding

`erpnextswiss.scripts.bank_camt_preview.preview_camt_archive` accepts the original
ZIP bytes, one supported camt profile, the configured company and its explicit
list of Account names. BankMatchingScope rechecks current native permissions,
active Bank account type, company, IBAN and account currency. The archive does
not choose an ERP company. Equal IBANs in distinct companies never cause global
first-hit lookup. Equal IBANs in distinct currencies require the file currency;
missing or ambiguous mappings fail rather than pick the first account.

The entire ZIP passes the existing bounded admission and packaged XSD validation.
Every file, statement/notification and its booking/balance currencies is bound
before the first financial candidate query. Invalid late files/accounts return
no partial preview. No new schema download or parser dependency is introduced.

The caller must still resolve these configured accounts from the authorized bank
connection. This helper is not itself a gateway authentication boundary or proof
that user-supplied account lists describe an EBICS contract.

## Existing engine, intact evidence

- Both 053 Stmt and 054 Ntfctn are traversed structurally, including multiple
  files/units, prefixed namespaces and UTF-16. Every unit keeps its own account.
- Original XML remains byte-exact in BankArchive, with archive/file SHA-256.
  Entry working copies are not originals and must not replace them in storage.
- Message, statement, sequence, page, date, copy indicator, balance and entry
  metadata are retained. Zero-entry statements and signed balances remain present.
- Money evidence remains decimal text. Decimal arithmetic checks detail sums and
  opening plus booked movements against closing balances without float rounding.
- Only standard fields enter the existing descendant-based matcher. Supplementary
  and foreign-namespace payloads cannot inject a second Amt, TxDtls or reference.
- The existing matcher gains an opt-in XML working-copy mode. It preserves escaped
  text, prefers explicit detail Amt to optional TxAmt, and does not choose an
  unrelated InstdAmt as an arbitrary descendant fallback. Existing default/manual
  paths and return fields remain unchanged. No existing matching rule is replaced.
- Results remain grouped with their source entries even if the old matcher
  suppresses an already-recorded payment. The suppression count is explicit;
  source rows are not deleted. The entry-index marker is internal to the adapter.
- The adapter invokes `read_only=True`: no automatic logs, payment writes or commits.

Amount interpretation follows the distinction in SIX SPS 2025 v2.2, sections
3.3 and 4.1.7: TxAmt can be the pre-conversion interbank amount and must not
silently replace a booking amount. D-level batch conversion can differ from
C-level conversion; incompatible currency/sum evidence requires review rather
than a guessed exchange allocation. Primary reference:
[SIX Cash Management v2.2](https://www.six-group.com/dam/download/banking-services/standardization/sps/ig-cash-management-sps-2025-en.pdf).
The bank-specific profile and release-compatibility acceptance remain separate.

## Explicit review states, not silent omissions

Pending/non-BOOK entries, reversals/returns, missing booking dates, inconsistent
detail sums/currencies and legacy settings that would multiply a batch amount
or overwrite a detail direction retain source/metadata with `review_required`.
The engine is not called for these rows. An explicit single-entry amount setting
continues to use the one booking amount; no new FX rate is inferred.

OPBD/CLBD checks report matched, mismatch, not_available, or
requires_page_assembly. A paginated message is not certified complete by this
preview. Source ordinal/hash identity is not business deduplication: no claim
of cross-file duplicates, cancellation identity or 053/054 overlap resolution.
The existing engine's candidate floats and matches must not serve as unchecked
financial write instructions. Every result is a preview, not import approval.

The limits are 64 explicitly configured accounts, 256 statement/notification
units and 10000 source entries, in addition to the archive/XML admission budgets.
These are explicit rejection limits, not pagination or partial processing.
Combined maximum-resource and live-bank capacity acceptance remains open.

## Verification

Nine new pure tests cover profiles/multiple files, original provenance, UTF-16
prefixes and escaped text, supplementary-field isolation, exact decimal/signed
balances, no partial malformed input, size counts, batch ambiguity and dates.
All 37 pure admission/preview tests and all 35 isolated helper tests pass locally.

Eight new native integration tests exercise the actual existing matcher and
Frappe queries for credit/debit, invoice/company binding, currency-specific
accounts, source provenance after suppression, no-write calls, late invalid
input, review states and wrong descendant amount fallback. They are release
gates in full app CI and again after HRMS installation; their commit-specific
GitHub result must be inspected before claiming the native gate passed.

## Still required

Gateway authentication/configuration, controlled durable import lifecycle using
the preserved original, complete pagination, safe statement/business identity,
cross-message deduplication, old ebics_statement write-path separation, restore,
approved bank pilot and deployment remain open. No production source/schema or
financial data change, bank initialization, key action, download or payment is
performed by this work. All original fourteen platform packages remain in scope.
