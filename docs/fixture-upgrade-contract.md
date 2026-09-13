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
