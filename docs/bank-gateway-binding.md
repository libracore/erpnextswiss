# Server-owned gateway handover binding

Implementation candidate, acceptance pending for the actual commit. No deployment,
active bank connection, HTTP API, credential or scheduler is introduced. Existing
reconciliation and Payment Proposals remain the only workflows; this is transport
integration, not a new financial process.

## Existing components connected

`TransferJournal::handover(ReadRequest)` authenticates a stored encrypted original
and exports its exact bytes plus a versioned envelope. It makes no bank call and
changes neither the bank receipt nor ERP state. `stage_gateway_archive` and
`receive_gateway_archive` validate that envelope and use the existing native
handover transaction helpers. PHP and Python agree on the existing request hash.

Metadata cannot select ERP accounts, companies or user identity. Unknown fields,
wrong site/connection/participant, altered hashes/sizes, invalid profiles/dates or
out-of-range segments fail closed. Bank receipt status remains separate from ERP
persistence and import approval. A stored unconfirmed bank receipt is not discarded
and must not cause a second bank download merely to retry ERP delivery.

The receipt retains immutable source metadata: full read request, request identity,
bank transfer ID, segments, original hash/size and gateway reception timestamp.
An existing source reference cannot acquire different metadata even for identical
ZIP bytes. Bank receipt status is intentionally not part of that immutable record:
it may become confirmed later in the authoritative gateway journal.

## Trusted configuration

The receiving Frappe site's `bank_gateway_receive` configuration is disabled when
absent. Its exact shape is:

- `version`: integer `1`; `enabled`: boolean `true` only after explicit review.
- `site`: exact current Frappe site-directory identity, preventing accidental use
  of a copied configuration on another site.
- `bindings`: at most 64 opaque alias keys, each resolving to the following fields.
- `gateway_site`, `gateway_connection`, `participant`: exact opaque identities
  configured in the gateway, not bank-supplied or request-selected values.
- `connection`, `company`: existing authorized ERP document names.
- `users`: explicit receiving ERP operators (maximum 64). They must still possess
  Accounts Manager or System Manager and actual current document permissions.
- `accounts`: 1-64 objects containing only `account`, canonical uppercase `iban`
  without spaces, and `currency` (`CHF` or `EUR`). Account and IBAN must be unique.

Aliases must not claim the same ERP connection/account or the same gateway source
identity. Ambiguous ownership fails closed even when the selected alias alone
would be valid. This supplements, not replaces, disabling the legacy sync path.

No account values, API tokens or bank credentials are placed in repository examples.
The mapping is not editable through a newly exposed DocType, portal or payload.
Current company, IBAN, currency, enabled bank-account state, H005/CH connection
profile and disabled legacy sync are checked inside the locked staging transaction.
Mapping and rights are checked again after commit. The native configuration loader
is called with `cached=False`; request-local `frappe.conf` is not authoritative for
this check. Revocation then suppresses a
success acknowledgement without pretending that committed data was rolled back.
Recovery keeps the same source reference after the configuration is reviewed.

## Authentication remains a release gate

The mapping and envelope hash are NOT proof of sender authenticity. The internal
caller must obtain the original from the trusted gateway over the future verified
channel; these functions are not whitelisted or reachable as public RPC. No proxy
header, self-asserted certificate identity or arbitrary account list is trusted.
Internal mTLS, secret provisioning, least-privilege service identity, operational
configuration UI and controlled activation remain unfinished. Native Frappe
authentication and permissions must be retained if an API is later added; see the
[official REST API contract](https://docs.frappe.io/framework/user/en/api/rest).

The integration test passes data between isolated processes, not across deployed
mTLS. It uses the real PHP SDK with a scripted signed bank response, real encrypted
SQLite journal and real Frappe/MariaDB commits. Network is disabled for the gateway
test container. Synthetic test fixtures are the only source of identities/keys.

## Verification and remaining work

Native tests exercise configured user/site boundaries, payload identity injection,
current account/connection drift, both profiles/currencies, configuration changes
between preparation and staging, immutable provenance and unchanged originals.
The process test revokes the real test-site mapping from another process after an
actual commit while the receiver still has a stale local configuration, requires no success
acknowledgement, then replays in another process with one original and one receipt.
The standard app suite, post-HRMS checks and existing workspace comparisons remain
enabled. Actual run results must be recorded against the tested revision.

Not completed by this increment: authenticated HTTP/queue transport, business-level
deduplication and 053/054 overlap, statement pagination, final native import,
encrypted ERP file storage/backup, restore, real-bank pilot and deployment.
