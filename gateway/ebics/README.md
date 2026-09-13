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
- `ReadClient` is the receiver's required SDK composition. It installs
  `BoundedZlib` through native `EbicsClientOptions::setZipCompressor` and requires
  an injected HTTP transport, with no implicit network fallback. It exposes only
  BTD execution; it is not an authorization layer or a trusted connection binding.
- Outer zlib input retains the SDK's 10 MiB cap; output is limited to the journal's
  32 MiB original limit before persistence and acknowledgement. Native zlib checks
  format/checksum; no compression algorithm or bank-file parser is reimplemented.
  Invalid, truncated, checksum-damaged or oversized data fails closed. Inner ZIP
  and XML admission is now a separately tested read-only Swiss-app helper, not
  connected to the local journal through an internal server-bound handover, but
  not deployed gateway transport or a financial import. See
  [file admission and existing-import boundaries](../../docs/bank-file-admission.md).
- `ReadClient::https()` selects `HttpsTransport` for a trusted configured endpoint.
  Native cURL performs HTTPS POST with certificate/hostname verification, TLS 1.2
  or newer, no redirects, environment proxies, HTTP decompression or automatic
  retries. Requests are capped at 1 MiB, headers at 64 KiB and response bodies at
  8 MiB through callbacks before XML DOM construction, including chunked bodies.
  A request timeout is at most 30 seconds; connection timeout at most five seconds.
- Response XML uses native XMLReader and the SDK Response DOM with `LIBXML_NO_XXE`
  and `LIBXML_NONET`, without entity substitution or DTD loading. DTDs, excessive
  depth (>64), node events (>4096) and attributes per element (>128) are rejected
  before constructing the DOM. No huge-parser mode or external fetch is enabled.
  Error messages do not include server bodies, XML error details or full URLs.
- A mandatory per-order `DownloadBudget` bounds all injected transports to at most
  64 declared segments, 65 HTTP exchanges (including receipt), and 20 MiB of
  serialized response XML in total. A monotonic 120-second deadline is checked
  before and after each HTTP exchange. It does not preempt local crypto/storage;
  an in-flight HTTPS exchange remains bounded by its own 30-second timeout.
  Limits reset only for a new order. Late receipt responses leave a stored original
  unconfirmed and local replay never blindly repeats its bank transfer.
- The SDK acknowledgement closure first commits the encrypted original and
  metadata to SQLite, then opens an independent connection and authenticates the
  stored bytes. Only successful persistence returns `true` to the SDK receipt
  phase. SDK response signatures are not bypassed.
- `TransferJournal::handover` exports a stored authenticated original and immutable
  source envelope without another bank call or receipt change. The Swiss-app
  receiver derives accounts/company from reviewed site configuration and verifies
  current mappings inside its transaction and after commit. This is an internal
  data-flow connection, not sender authentication or an operational service. See
  [server-owned handover binding](../../docs/bank-gateway-binding.md).
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
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m --memory 512m --cpus 1.5 \
  -e KT_GATEWAY_SIZE_TEST=1 kt-bank-gateway-test \
  php -d memory_limit=256M tests/full_size.php
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --memory 256m --cpus 1.5 \
  -e KT_GATEWAY_HTTPS_TEST=1 kt-bank-gateway-test \
  php -d memory_limit=128M tests/https_transport.php
```

The SDK is real; the HTTP bank is scripted and has no network fallback. Synthetic
keys/certificates exist only in test memory. Tests cover real signing/encryption,
segmented downloads, tampered signatures, binary originals, encrypted receipts,
metadata tampering, tenfold replay, scope conflicts, transaction rollback,
independent-process restart/locking, SIGKILL at the receipt boundary, failed
storage and uncertain bank receipts. The isolated 1 MiB tmpfs test induces actual
SQLITE_FULL and verifies no acknowledgement, no partial row and later recovery.
It refuses to fill arbitrary directories or the host filesystem.

The decompression regression generates a synthetic 256 MiB expansion using
incremental native deflate without allocating the expanded input. In an isolated
96 MiB PHP subprocess, the default SDK reaches an actual memory-limit failure;
the constrained decoder rejects the same input and still decodes an exact
32 MiB original. Its actual peak memory is reported. The SDK integration tests
verify no persistence/receipt for invalid or over-limit data and successful
recovery; existing signature, durability and replay tests use `ReadClient` too.

PHP 8.5's `gzuncompress` allocation-growth loop can return more than its
`max_length` argument when the stream ends within the final grown buffer. The
native limit bounds allocation growth, and an additional exact length check
enforces the admission limit. Tests exercise the limit plus one byte and a larger
last-buffer overrun, not only a large compression bomb. Sources:
[PHP API](https://www.php.net/manual/en/function.gzuncompress.php),
[PHP implementation](https://github.com/php/php-src/blob/PHP-8.5/ext/zlib/zlib.c).

Decompression-only success is not an end-to-end capacity proof. `full_size.php`
also checks the complete 32 MiB signed synthetic transfer, encryption, durable
independent readback, receipt and local replay. It uses a separate 256 MiB PHP /
512 MiB container budget with 128 MiB tmpfs because journal/crypto/readback copies
also consume memory. An initial measured PHP peak was 171,986,944 bytes; do not
deploy a future worker with the small-test 128 MiB PHP limit or count tmpfs as free
container memory. Real HTTP buffers/concurrency require their own capacity test.

The HTTPS tests use real cURL and a loopback-only TLS server inside a container
with external networking disabled. Synthetic TLS and EBICS keys exist only in its
temporary test directory/memory. Tests reject an untrusted certificate, wrong
hostname, altered endpoint, environment proxy routing, oversized/chunked body,
oversized headers, redirect, HTTP encoding, malformed XML and timeout. The exact
8 MiB body boundary remains accepted. Request logs prove no automatic retry or
redirect follow. A full signed SDK download and receipt traverses this actual
HTTPS transport and preserves its binary original; local replay produces no HTTP.

The pinned SDK's default HTTP XML loader was experimentally shown to expand a
synthetic local-file entity (`LIBXML_NOENT` is set there). The new loader rejects
DTD inputs, including UTF-16, and an instrumented external-entity loader receives
zero calls. Normal built-in XML escapes and signed bank responses still work.
The SDK is not patched; the hardened class implements its HTTP extension contract.
Sources: [cURL body callback](https://curl.se/libcurl/c/CURLOPT_WRITEFUNCTION.html),
[libxml security flags](https://www.php.net/manual/en/libxml.constants.php).

`ReadClient` still permits deliberate programmatic transport injection for testing
and future approved adapters. Its aggregate budget cannot retroactively protect a
custom transport that has already parsed or fetched unsafe data: real networking
must use `ReadClient::https()`/`HttpsTransport` or an equivalently reviewed adapter.
Endpoint/CA values are not permission checks. No user-facing route accepts URLs
or curl options. Trusted connection storage, DNS/egress binding, internal mTLS and
bank-approved limits remain release gates; no live bank configuration is supplied.

## Still required before any activation

1. Trusted site/connection/participant binding, bank-approved configuration,
   mTLS, allowlisted egress, certificate/fingerprint and keyring lifecycle.
2. Connect the tested inner ZIP/XML admission and prove full worker capacity/concurrency with
   real transport at worst-case sizes. HTTPS envelopes, aggregate segments and
   outer zlib are bounded; the separate ERP admission must still be invoked, and
   its isolated test does not prove
   every combined HTTP/DOM/base64/AES/journal memory peak. Confirm these limits
   against the approved bank profile before any pilot.
3. Operation admission/status, no-data/error journaling, pending receipt handling,
   retention, key rotation, encryption-aware backup and isolated restore proof.
4. Account/currency mapping and controlled handover to existing ERP import and
   reconciliation, content/business idempotency across different request IDs,
   balance-only statements and 053/054 overlap. No new reconciliation engine.
5. Company/account authorization and endpoint/file/job/ERP hook regression tests,
   inactive migrations, CHF/EUR bank pilot and approved rollout/rollback.

No actual bank initialization, key change, live download or payment was performed.
