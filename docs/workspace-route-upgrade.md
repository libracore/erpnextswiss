# Workspace route compatibility

The v16 fresh-install check exposed a route collision between six app-owned
redirect Pages and the real Workspaces. Standard JSON import allowed these
duplicates, but a normal subsequent Workspace save rejected them. Disabling
Frappe's route validation would hide the failure and leave Workspace editing
broken, so it is not used.

## Compatibility strategy

- Workspace documents, labels, contents, links, roles, desktop icons and layouts
  are unchanged by this route adjustment.
- The four canonical workspace slugs resolve through Frappe's own workspace map.
  `/desk/erpnextswiss` and `/desk/qr-rechnung-e-rechnung` use the existing
  `frappe.re_route` extension point and Frappe's native workspace slug.
  Aliases are registered only if that target is in the current user's allowed
  boot workspaces. No permission or workspace entry is invented or overwritten.
- Retained Page references redirect on every `on_page_show`, not only their first
  load. Native slug targets preserve the active navigation item as well as the
  Workspace contents. No router or sidebar method is patched.
- The obsolete Page JSONs are removed from sync. Fresh installs do not create
  duplicate proxies. Existing app-owned proxies are renamed by native Frappe
  into `kt-swiss-route-<old-name>` in `before_migrate`, before Frappe's orphan
  entity cleanup. The retained records become `standard = No`, so that subsequent
  orphan cleanup does not delete site-specific history whose old JSON was retired.
- Native rename retains roles, child records, Custom Role links, attachments,
  comments and Version history. No merge, delete or history purge is performed.
  The old proxy `page_name` and title remain intact. Technical Page assets remain
  available so Page references updated by Frappe still open their Workspace.
- A foreign module, a nonstandard or repurposed Page, or an occupied target name
  stops the whole preflight before the first rename. No customer customization
  is overwritten to make CI pass. Migration owns the transaction; the helper
  neither commits nor touches source files.

The read-only production inventory found expanded HR roles on the root proxies,
different settings roles, and existing histories. These are preserved through
native rename, not discarded as deviations from the original three-role JSONs.
No production rename or migration has been performed as part of this inspection.

## Verification and remaining gate

- Seven isolated migration-contract tests and nine Node route-registration/visit tests
  pass locally. Existing inventory, artifact and Item maintenance tests remain
  part of the same run (21 isolated Python tests in total).
- Native Frappe tests cover fresh-install Workspace saves with route validation,
  a legacy upgrade with retained Version/comment/Custom Role/File/role records,
  technical Page assets, repeated upgrade calls and modified-proxy rejection.
  Their actual execution is a separate CI gate, not implied by isolated tests.
- Browser navigation, native full-app tests and production-image upgrade checks
  remain release gates. Reconciliation and payment proposals remain existing
  workflows; no parallel payment UI is introduced.

## Executed CI evidence, 13 September 2026

Commit `84bff65e3484a60e55e3ba82de9b1cc36a00d3db` passed the full
[Swiss CI run](https://github.com/philippbenkert-maker/erpnextswiss/actions/runs/34726493794)
and the [offline banking run](https://github.com/philippbenkert-maker/erpnextswiss/actions/runs/34726493778).
The Swiss run includes 31 full-app tests, five focused native migration tests,
three native Item maintenance tests, 21 isolated tests and 766 byte-identical app
resources in both distribution formats. These counts overlap; do not add them
as distinct test cases.

The browser fixture created six legacy Pages with sentinel Versions/comments.
Two actual `bench migrate` runs each retained all six histories. Twelve Chromium
comparisons at 1440x1000 and 390x844 passed for Workspace text and block geometry;
36 screenshots were retained and the five distinct Workspaces visually inspected
in both viewports. This is synthetic CI-site evidence, not a production migration.

Pixel inspection additionally found that the explicit `Workspaces/<name>` route
omitted the native Home selection on four desktop comparisons. Contents were
unchanged; the difference was confined to the sidebar selection. The follow-up
uses native slug URLs and adds complete screenshot equality and two warm Page
revisits to every comparison. Its actual execution must be verified separately;
the earlier green run does not prove these stronger assertions.

The eight PDF wrapper tests also passed against the current production base image
in an isolated, network-disabled, read-only container with no production mounts.
Only Frappe imports/dependencies were real there; the PDF renderer and permission
checks were mocked by those unit tests. This is not a full PDF rendering proof.

Still open: production-image/site upgrade and rollback acceptance, broader account
and payment workflow regression, actual bank adapter delivery and approved bank
pilot. No production migration, bank contact or deployment occurred in this increment.
