# Bank file admission before existing ERP imports

Status: tested read-only adapter component, **not yet an activated import**.
Existing reconciliation, payment proposals, permissions, exports and layouts are
unchanged. No replacement business parser, new dependency, bank key or bank call.

## Entry points and existing components

`erpnextswiss.scripts.bank_file_admission.read_bank_archive(payload, profile)`
accepts immutable ZIP bytes and an explicitly selected supported profile.
It returns an immutable manifest with SHA-256 of the original archive and a tuple
of byte-exact XML files, original names and per-file SHA-256. File content/names
are omitted from dataclass representations. No extraction to disk, callback,
database, Frappe import or financial operation occurs. A failure in a later member
returns no partial result. The encrypted archive remains the caller's responsibility.

`validate_camt_xml(content, profile)` is the shared XML admission primitive, not a
transaction parser. It uses the existing packaged `camt.053.001.08.xsd` and
`camt.054.001.08.xsd`, unmodified. Native lxml schema validation follows a bounded
event-only XML pass. No monetary calculations, IBAN matching or data normalization.

The code inventory confirms why simply invoking the current EBICS import is not
an acceptable read-only handover: `ebics_connection.get_transactions` acknowledges
before ERP persistence, calls `process_transactions`, and deletes zero-transaction
statements. `ebics_statement.parse_content` selects the first IBAN account,
interpolates an XML-derived IBAN into SQL and commits internally. Its transaction
processor can submit payments. These are existing source-path observations, not
claims that a production financial operation was performed or compromised.

The new bank adapter must avoid those automatic processing paths. The current
Bank Wizard matching logic remains the reuse target after explicit company/account
binding, namespace/multi-statement/054 compatibility and side-effect tests.
Do not silently reuse first-account selection, delete balance-only files or create
a parallel matching engine to work around integration defects.

## Admission limits

- 32 MiB original ZIP; classic single-disk ZIP end record, no SFX or ZIP64 end
  directory. Local ZIP64 member headers and streaming data descriptors are tested.
- 64 members including directory markers, central directory at most 256 KiB.
  The fixed end-record budget is checked before ZipFile allocates member objects.
  The native parser must then confirm the declared member count.
- 8 MiB per XML file; 32 MiB aggregate expansion. Stored/deflated regular files and
  empty directory markers only. No nested archives, links, devices, encryption or
  unsupported compression. Safe relative names at most 255 UTF-8 bytes; reject
  duplicate names including case/Unicode normalization collisions, control
  characters, NUL truncation, absolute paths, backslashes and traversal segments.
- XML depth 64, elements 100000, attributes per element 128; no recovery or huge
  parser mode. DTDs are rejected by a native parser event, including UTF-16 input.
  External resolver always denies resources. Document schemaLocation is not used.
- Exact requested ISO namespace and existing XSD required. CHF/EUR examples,
  multiple statements/notifications, XML namespace prefixes, UTF-16, built-in
  escapes, optional sequence numbers and zero-entry statements are tested.

The ZIP library's `read` alone was experimentally shown to return a valid prefix
when a malformed member declares a shorter file_size and matching prefix CRC.
This occurred for stored and deflated members on both tested Python runtimes.
The admission path therefore lets ZipFile validate member/header/ranges, then
uses bounded native zlib decoding and requires actual stream EOF, full length and
CRC. Stored members must have equal compressed/uncompressed sizes. No compression
or transaction algorithm is reimplemented. No compressed trailing data is ignored.

Sources: [Python ZIP API](https://docs.python.org/3/library/zipfile.html),
[CPython ZIP implementation](https://github.com/python/cpython/blob/3.14/Lib/zipfile/__init__.py),
[lxml parsing](https://lxml.de/parsing.html).

## Evidence and release gates

28 tests pass locally and in a separate container based on the existing production
image, with no network, read-only source mount, no site/configuration/data volumes,
unprivileged UID, dropped capabilities, 256 MiB container and virtual-memory limit.
That image has Python 3.14.7, lxml 6.1.3, libxml 2.14.6; measured peak RSS 114064 KiB.
The module was imported from the test mount and Frappe was not imported.
Tests include a streamed synthetic 64 MiB expansion with forged metadata, actual
8 MiB XML / 32 MiB aggregate boundaries, corrupt CRC/header, partial input, wrong
profiles/types, no partial output, and zero external resolver calls on DTD attacks.
The separate bank CI now includes this test set with lxml 6.1.1 and a 256 MiB
process budget; its result must be verified for the eventual commit, not assumed.

This is not combined gateway/ERP capacity proof or bank approval. Before activation:
authenticated mTLS handover and encrypted-original identity, company/account/currency
binding, real supported-bank profile/limits, semantic validations (e.g. balance and
053/054 overlap), business idempotency, existing-import compatibility, explicit
non-posting policy, quarantine/error statuses, bank-independent restore and an
approved pilot are still required. XSD validity alone does not prove any of these.

The helper is intentionally not whitelisted, scheduled or connected to a live bank.
No migration, financial record or production source was changed by this increment.
The original 14 platform packages remain part of the active goal.
