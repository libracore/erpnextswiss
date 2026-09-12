# Swiss bank transport foundation

Status: offline-tested library, **not an operational gateway**. No public endpoint,
bank configuration, scheduler, key initialization, payment upload or ERP writer is
registered. The default runtime command deliberately exits with code 2. Do not
deploy this as a working bank connection.

Existing reconciliation, payment proposals, exports, approvals and screens in
ERPNextSwiss remain authoritative and unchanged. This component only prepares
reliable bank transport for their later, separately tested integration.

## Implemented boundary

- `ReadRequest` admits only opaque configured identities, exact UTC calendar
  dates (at most 32 inclusive days), camt.053.001.08 and camt.054.001.08.
- `DownloadReceiver` constructs BTD/EOP or BTD/REP, CH, ZIP, version 08. It uses
  the SDK's TEXT result mode to preserve the complete decrypted ZIP bytes rather
  than unpacking or importing them. No initialization or upload order is exposed.
- The SDK acknowledgement closure first commits the encrypted original and
  metadata to SQLite, then opens an independent connection and authenticates the
  stored bytes. Only successful persistence returns `true` to the SDK receipt
  phase. SDK response signatures are not bypassed.
- XChaCha20-Poly1305 through libsodium protects original/receipt BLOBs and binds
  site, connection, participant, request, profile, dates, bank transaction ID,
  segment count, original hash, size and reception timestamp as authenticated data.
  Opaque metadata and original byte counts/hashes are not encrypted.
- SQLite uses DELETE rollback journaling and synchronous=EXTRA on an owner-only
  local directory. This assumes a storage/filesystem stack that honors fsync;
  tests do not prove behavior during physical disk failure or power loss. Do not
  use network filesystems or assume replicated/multi-host locking.
- Per-participant flock prevents simultaneous transport in processes sharing this
  journal directory. Request IDs are bound to site/connection and the full scope.
  A stored request is replayed locally, including after an uncertain bank receipt.
  Changed scope or conflicting original for the same identity is rejected.
- Original and bank receipt are separate states. A timeout or process termination
  after persistence leaves `unconfirmed`, never an invented bank confirmation.
  No automatic second download is attempted for that stored request.

`TransferJournal::initialize()` is explicit and refuses existing files. Opening
an absent journal, an unsafe path, a different key ID or a wrong key fails closed;
no key generation, reset or automatic key rotation occurs. Configuration and keys
must eventually come from an authenticated, trusted server-side binding, not
request values. These classes are not an authorization layer.

## Dependencies and update contract

Application code retains the repository AGPL license. The only Composer runtime
library is `ebics-api/ebics-client-php`, MIT, version 3.2.1, reviewed commit
`c0cd3d448fa01ea0442e72b2720be0d371070c12`. No premium REST service, subscription,
installation fee or FPDF component is required by this increment. Native PHP,
libsodium, SQLite and Alpine package notices remain applicable in the image.

During resolution on 13 September 2026, Packagist mapped 3.2.1 to `11c2caf...`,
while the verified Git tag mapped to the reviewed commit above. Composer therefore
uses the Git repository and committed lockfile; the offline test checks the
installed commit, not just a mutable version string. A future dependency update
requires reviewing source changes and updating the test pin deliberately.
There is no runtime `composer update` or bank contact during image construction.

PHP 8.5 and Composer base image digests are pinned in the Dockerfile. Git is used
only in the dependency/tooling build stage, not added to the runtime. Alpine
package versions are still repository-resolved, so a bit-reproducible build and a
complete image SBOM are **not** yet claimed. Composer install validates required
extensions without platform-requirement exemptions or executable plugins/scripts.

Official sources: [SDK source and MIT license](https://github.com/ebics-api/ebics-client-php/tree/c0cd3d448fa01ea0442e72b2720be0d371070c12),
[AKB BTF mapping](https://www.akb.ch/documents/30573/89691/ebics-3.0-umstellung.pdf),
[AKB EBICS onboarding](https://www.akb.ch/firmen/bezahlen/software-anbindungen/ebics).
Published bank profiles do not establish permission, credentials or acceptance
for any actual account.

## Offline verification

From this directory:

```sh
docker build --target test -t kt-bank-gateway-test .
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --memory 256m --cpus 1.5 kt-bank-gateway-test
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --tmpfs /kt-disk-full:rw,noexec,nosuid,uid=10001,gid=10001,mode=0700,size=1m \
  --memory 256m --cpus 1.5 -e KT_GATEWAY_DISK_FULL_TEST=1 \
  kt-bank-gateway-test php tests/full_disk.php
```

The SDK is real; the HTTP bank is scripted and has no network fallback. Synthetic
keys/certificates exist only in test memory. Tests cover real signing/encryption,
segmented downloads, tampered signatures, binary originals, encrypted receipts,
metadata tampering, tenfold replay, scope conflicts, transaction rollback,
independent-process restart/locking, SIGKILL at the receipt boundary, failed
storage and uncertain bank receipts. The isolated 1 MiB tmpfs test induces actual
SQLITE_FULL and verifies no acknowledgement, no partial row and later recovery.
It refuses to fill arbitrary directories or the host filesystem.

## Still required before any activation

1. Trusted site/connection/participant binding, bank-approved configuration,
   mTLS, allowlisted egress, certificate/fingerprint and keyring lifecycle.
2. Bounded transport/segment sizes and timeouts, bounded outer decompression and
   safe ZIP/XML validation. The SDK defaults are not sufficient evidence here;
   the current 32 MiB journal limit runs after transport/decompression.
3. Operation admission/status, no-data/error journaling, pending receipt handling,
   retention, key rotation, encryption-aware backup and isolated restore proof.
4. Account/currency mapping and controlled handover to existing ERP import and
   reconciliation, content/business idempotency across different request IDs,
   balance-only statements and 053/054 overlap. No new reconciliation engine.
5. Company/account authorization and endpoint/file/job/ERP hook regression tests,
   inactive migrations, CHF/EUR bank pilot and approved rollout/rollback.

No actual bank initialization, key change, live download or payment was performed.
