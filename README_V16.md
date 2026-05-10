# ERPNextSwiss v16 fork

This branch is based on upstream `libracore/erpnextswiss` branch `v2025` and is adjusted for ERPNext/Frappe 16 deployment.

## Changes

- Removed `frappe` from Python package dependencies so Frappe Cloud/`uv` does not try to resolve Frappe as a pip package.
- Added Bench app dependencies for Frappe and ERPNext `>=16.0.0,<17.0.0`.
- Added explicit setuptools build backend and dynamic version lookup from `erpnextswiss.__version__`.
- Fixed the generated template bundle path in `app_include_js`.

## Compatibility note

This branch is intended to make the app installable on Frappe/ERPNext 16. ERPNextSwiss is a broad app with accounting, banking, HR and integration features, so production use still requires a full `bench migrate` and functional checks on a staging site.
