# Swiss Custom Field import and export contract

## Reproduced failure

The no-HRMS test at source `4640331e44c1af46b0d8682d2bb9b35fa736f57d`
failed in [native CI](https://github.com/philippbenkert-maker/erpnextswiss/actions/runs/34727835857).
Installation returned success, but Frappe stopped importing `custom_field.json`
at the first missing Expense Claim DocType. Its exception handler surrounds the
entire file import, not each record. Of 39 fields applicable without HRMS, 22
were absent. A read-only `SELECT is_proposed FROM tabPurchase Invoice LIMIT 0`
failed with native MariaDB error 1054. This was a synthetic fresh installation,
not evidence of missing production fields or incorrect financial postings.

Affected fields include payment-proposal flags, Customer banking details,
Payment Entry.camt_amount, early-payment discount settings, payment reminders
and Abacus export flags. They are existing Swiss functions, not new banking
features to build.

## Update-safe correction

- Keep 39 core/ERPNext fields in `fixtures/custom_field.json`.
- Keep the two existing Expense Claim fields in `fixtures/hr_custom_field.json`.
  A missing optional HR DocType can skip only that file. Installing HRMS and
  running migrate later imports those same definitions.
- Preserve all 41 field names, types, labels, defaults, ordering references,
  visibility, permissions and other original metadata. No field is renamed,
  removed from a database or reinterpreted; no new payment UI or logic is added.
- Use native Frappe fixture export entries with exact name filters and the `hr`
  prefix. Re-export keeps the same grouping and cannot collect unrelated site
  Custom Fields from other apps. No custom import engine or monkeypatch is used.
- Both fresh installation and ordinary migration use native fixture sync. No
  application code edits financial records or changes payment approvals.

## Verification contract

Isolated tests compare a canonical SHA-256 of all 41 definitions against the
pre-split snapshot, and verify exact one-to-one correspondence between export
filters and fixture files. An intentional future field change requires review
and an explicit snapshot update; it must not silently broaden export ownership.

Native tests check every applicable field in actual DocType metadata and query
critical payment columns without reading financial rows. The native exporter is
run twice against a temporary output directory, with a synthetic unrelated Custom
Field record in a rolled-back transaction. Only source-owned fields may appear;
both exports must be identical. The test avoids schema DDL for the foreign row.

CI also checks these contracts after two no-HRMS migrations, then installs actual
HRMS v16 and repeats migration and field/export checks. Execution results must be
recorded separately; adding a test is not a successful runtime proof.

Production rollout still requires an inventory of existing field definitions,
candidate-image/site migration and restore/rollback acceptance. Native Frappe
fixture sync can overwrite a customized field that has the same owned name;
those differences must be reviewed before deployment. No production migration,
financial posting, bank initialization or payment is authorized by this document.

## Executed verification, 13 September 2026

Source `cda02266468923c6ed74d433797d92bb7f505658` passed the full
[Swiss CI](https://github.com/philippbenkert-maker/erpnextswiss/actions/runs/34728128243)
and [offline bank CI](https://github.com/philippbenkert-maker/erpnextswiss/actions/runs/34728128259).
The native suite passed 34 tests. All three field/export tests passed after two
no-HRMS migrations, then after each of two migrations with actual HRMS v16 added.
The existing payment columns are queryable in both configurations. The 23 isolated
tests, nine Node route tests and 768 byte-identical packaged resources also passed.
Counts of focused and full-app tests overlap and must not be added together.

The unchanged Workspace browser checks passed 12 route/viewport comparisons with
60 retained screenshots, including two warm revisits per route. Cold views are
byte-identical; warm comparisons differ by at most 36 pixels with a maximum
channel delta of 1/255. Text and block geometry remain identical. Desktop/mobile
payment Workspace samples were also visually inspected. This is synthetic
CI-site evidence, not proof of production migration or every payment operation.

## Read-only production preflight

`scripts/swiss_fixture_inventory.py` compares every source-specified Custom Field
attribute supported by the running metadata, excluding record identity and audit
timestamps. It reports missing records, required/optional missing DocTypes and
changed attribute names. Unsupported source attributes are listed separately;
they are not silently treated as matching. It never prints actual/default/option
values. Unspecified properties, Property Setters, financial rows and database
column types are outside this metadata check.

Run it using the candidate fixture directory, not an older installed export:

```sh
env/bin/python /path/to/swiss_fixture_inventory.py \
  --site SITE --sites-path /absolute/bench/sites \
  --fixtures-dir /absolute/candidate/fixtures
```

The process starts a database-enforced read-only transaction, reads metadata as
Administrator, then rolls back and destroys the connection on success or failure.
It has no bank client, scheduler or import/mutation endpoint. Four isolated tests
cover completeness, drift/redaction, missing targets and transaction cleanup;
all 27 isolated repository tests passed locally after adding this inventory.

The controlled production preflight at `2026-09-13T00:38:40Z` found all 41
candidate fields, no supported-attribute differences, no missing target DocTypes
and no unsupported source attributes. The exact candidate source SHA-256 values:

- `custom_field.json`: `cc163d2ee5c6b06e2acd3a29df173c9b690635d00519169a6e87085326c7b4ab`
- `hr_custom_field.json`: `33a7743e386798c9e0185c03d52a74d0dedfbd7efb7f5a8f34e2dae1ab6b3362`

Only a temporary diagnostic script and candidate definitions were copied; no
installed application source, financial data, field definition or production
schema was changed. This evidence does not replace candidate-image/site upgrade,
restore acceptance or existing financial workflow tests. Bank connection/handover
remains the delivery scope; reconciliation and payment proposals already exist.
