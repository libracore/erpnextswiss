# Bank file handover: internal staging contract

Status: implementation candidate, native CI acceptance pending. No active gateway
binding, bank operation, public API, scheduler or financial import is added here.
Existing reconciliation, Payment Proposals and their workspaces remain unchanged.

## Purpose and transaction boundary

`stage_bank_archive` validates the complete original ZIP through the existing
admission/parser/matching path before persisting a `Bank File Handover` and private
original File. This is a technical provenance journal, not a second bank ledger.
The connection must be readable/writable by the receiving Accounts Manager or
System Manager, have the correct company, and have legacy automatic sync disabled.
Every explicitly supplied account must currently be authorized and valid.

An opaque source reference is bound to the original bytes, connection, company,
profile and account scope. A repeated reference cannot change those bindings.
Identical bytes under a new source reference reuse the original, retaining the
additional receipt. The connection row is locked until the caller ends its
transaction. One handover holds at most 1,024 receipts and 64 accounts.

The helper does not commit. `commit_required: true` explicitly means that return
is NOT an acknowledgement of durable ERP persistence. The future authenticated
adapter must commit, then verify persisted state in an independent transaction
before acknowledging ERP handover. It must supply the account binding from trusted
server-side configuration, not from a bank payload or client request.

Failure rolls back the helper's SQL savepoint and file callbacks, preserving an
outer transaction. A database deadlock instead invalidates the entire transaction.
No legacy ebics Statement processing, Payment Entry submission or bank call occurs.

## Access and originals

Preview checks current connection/account/company rights and revalidates actual
stored bytes; it never reuses stale matching approval. Native document/list rights
are constrained accordingly. A v16 File extension also guards actual private URL
downloads, whose native owner check alone would otherwise bypass revocation.
Generic changes, detachments, publishing, copies and deletion of these originals
are rejected before native File mutation. Unrelated Files retain native behavior.

Original bytes are private Frappe files, NOT encrypted by this module. Encrypted
storage/backup and a tested restore remain release requirements. The admission
limit is 32 MiB, and any stricter native Frappe file-size policy still applies.
No global upload limit or existing File controller is replaced.

## Deliberately not yet claimed

- Cross-file business deduplication or camt.053/camt.054 overlap resolution.
- Multi-page statement assembly or final native Bank Transaction creation.
- Authenticated gateway configuration, bank initialization, keys or payment rights.
- Successful real commit/restart/concurrent receiver acceptance or restore.
- Production deployment or completed bank connection.

These remain requirements of the banking programme; staging is one implementation
step toward the existing import/reconciliation workflow, not its replacement.

## Verification

`test_bank_file_handover_native` exercises real DocTypes, SQL, File storage and
permissions using synthetic rollback-owned data. It covers replay, changed source
binding, both camt profiles, UTF-16, multi-unit files, callback rollback, stored
byte corruption, revoked file-owner access (including the native download lookup),
generic File mutation denial, install-time queries and unrelated File behavior.
CI runs the module as part of the app suite and again after optional HRMS install.
Passing results must be recorded against the actual commit before acceptance.
