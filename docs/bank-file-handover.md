# Bank file handover: internal transaction contract

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

The staging helper does not commit. `commit_required: true` explicitly means that
return is NOT an acknowledgement of durable ERP persistence. A caller composing
other ERP writes owns the commit and must restart its complete transaction if the
database rejects it. It must verify persisted state after commit before reporting
successful handover.

Failure rolls back the helper's SQL savepoint and file callbacks, preserving an
outer transaction. A database deadlock instead invalidates the entire transaction.
No legacy ebics Statement processing, Payment Entry submission or bank call occurs.

`receive_bank_archive` is a separate internal entry point for a dedicated receiver
transaction. It refuses pending caller writes or transaction callbacks, then ends
any previous read-only snapshot. Database deadlocks/snapshot conflicts during
staging restart the whole owned transaction, at most ten attempts with bounded
backoff. Global database isolation is unchanged. MariaDB's strict snapshot
isolation can reject locking reads as well as writes with error 1020; acquiring a
row lock alone is not sufficient. See the [MariaDB transaction documentation](https://mariadb.com/docs/server/ha-and-performance/standard-replication/enhancements-for-start-transaction-with-consistent-snapshot).

The dedicated receiver reports `committed: true, commit_required: false` only after
the actual commit and a new-transaction readback of the original bytes, hash,
receipt and current permissions. Commit errors are never automatically retried:
an after-commit failure can mean the data is already persisted. The future adapter
must retain the same source reference and retry through this idempotent entry
point, not invent another reference or assume rollback undid a successful commit.
No return value approves a financial import (`import_approved` remains false).

Both entry points require a future authenticated adapter to supply account binding
from trusted server-side configuration, not from a bank payload or client request.
Neither is an HTTP endpoint or a bank-side acknowledgement method.

## Access and originals

Preview checks current connection/account/company rights and revalidates actual
stored bytes; it never reuses stale matching approval. Native document/list rights
are constrained accordingly. A v16 File extension also guards actual private URL
downloads, whose native owner check alone would otherwise bypass revocation.
Generic changes, detachments, publishing, copies and deletion of these originals
are rejected before native File mutation. Unrelated Files retain native behavior.
The extension forces binary reads only for bank originals. Some valid ZIP bytes
also decode as UTF-16; allowing native text decoding and subsequent UTF-8 encoding
would corrupt those originals. Files are inserted once through the native File
controller with bytes, then verified against the received content.

Original bytes are private Frappe files, NOT encrypted by this module. Encrypted
storage/backup and a tested restore remain release requirements. The admission
limit is 32 MiB, and any stricter native Frappe file-size policy still applies.
No global upload limit or existing File controller is replaced.

## Deliberately not yet claimed

- Cross-file business deduplication or camt.053/camt.054 overlap resolution.
- Multi-page statement assembly or final native Bank Transaction creation.
- Authenticated gateway configuration, bank initialization, keys or payment rights.
- Database/container restart, power-loss durability or successful restore.
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

`bank_handover_process_acceptance` runs only on disposable CI `test_site`, with
synthetic data and real SQL commits. Eight independent processes race the first
creation and repeat source references. Separate processes verify one parent and
one original, all unique receipts, exact bytes and unchanged financial row counts.
It also covers whole-transaction rollback, an outer commit after caught staging
failure, rejection of pending caller work and an actual after-commit callback
failure followed by an independent replay. Financial row counts are not a proof
against arbitrary third-party field updates; the native side-effect and existing
matching tests remain necessary. These tests are not a real-bank pilot or restore.
