# ERPNextSwiss v16 fork

This branch is based on upstream `libracore/erpnextswiss` branch `v2025` and is adjusted for ERPNext/Frappe 16 deployment.

## Changes

- Removed `frappe` from Python package dependencies so Frappe Cloud/`uv` does not try to resolve Frappe as a pip package.
- Added Bench app dependencies for Frappe and ERPNext `>=16.0.0,<17.0.0`.
- Added explicit setuptools build backend and dynamic version lookup from `erpnextswiss.__version__`.
- Fixed the generated template bundle path in `app_include_js`.
- Added a Frappe v16-style workspace structure:
  - `Schweizer Buchhaltung` as the app entry workspace
  - child workspaces for `Zahlungsverkehr`, `QR-Rechnung & E-Rechnung`, `Schweizer MwSt` and `Schweiz-Einstellungen`
  - app tile, app home route and workspace sidebar records created/updated during install and migrate
- Fixed compatibility with current `factur-x` imports.
- Added `Aargauische Kantonalbank` as an enabled bank import profile using `CAMT.053 Bank Statement`.
- Enabled `CAMT.053` as a selectable bank import format in the legacy bank import page.

## QR invoice setup

For outgoing QR invoices use the workspace `Schweizer Buchhaltung > QR-Rechnung & E-Rechnung`.

Required setup:

- Maintain the company bank account in `Bank Account` with IBAN or QR-IBAN.
- Maintain company and customer addresses completely.
- Use the ERPNextSwiss QR print format on submitted `Sales Invoice` documents.

For incoming QR invoices use `QR-/ZUGFeRD-Assistent` or the QR/ESR fields on `Purchase Invoice`, depending on whether the supplier sends a QR PDF or only the payment information.

## Compatibility note

This branch is intended to make the app installable on Frappe/ERPNext 16. ERPNextSwiss is a broad app with accounting, banking, HR and integration features, so production use still requires a full `bench migrate` and functional checks on a staging site.

## Swiss Accounting Software overlap

This fork intentionally keeps QR invoice and ZUGFeRD functionality inside ERPNextSwiss, but it does not automatically migrate settings or disable overlapping features from `swiss_accounting_software`.

Known overlap areas:

- Swiss QR invoices
- CAMT/payment reconciliation
- pain.001 payment export
- Swiss accounting setup/settings

Do not uninstall `swiss_accounting_software` until QR invoices, payment imports and payment exports have been validated on the production site with this fork.
