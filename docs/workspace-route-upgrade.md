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
  comments and Version history. First-time retirement uses a plain rename without
  merge, delete or history purge. The old proxy title remains intact. Technical
  Page assets remain available so Page references updated by Frappe still open
  their Workspace.
- Repeated production updates can encounter the already-retired
  `kt-swiss-route-*` Page plus a freshly recreated app-owned legacy Page. In that
  specific idempotency case the recreated standard proxy is merged by Frappe's
  native rename API into the existing retired Page after both records are
  validated as ERPNextSwiss-owned. Missing roles are copied first; dynamic links,
  Versions, comments and attachments are then kept on the retired Page.
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

The stronger checks subsequently passed at source `00d6106` in run `34727410928`
and again at `cda0226` in run `34728128243`: 12 route/viewport comparisons,
60 retained screenshots, two warm revisits per route, cold views byte-identical,
and at most 36 warm pixels differing by one channel level. No layout region was
masked. The later run also verifies optional fixture installation with and without
HRMS; see [fixture upgrade evidence](fixture-upgrade-contract.md).

Run `34727001914` then passed native tests, both migrations and the first cold
full-viewport comparisons. Its first warm revisit differed at just 36 rounded-edge
pixels, each by one grayscale level (maximum channel delta 1/255); text and block
geometry were identical. Cold comparisons remain byte-exact. Warm comparisons now
allow at most 128 changed pixels with maximum channel delta 1/255, without masking
any region, and record actual deltas in the results. Comparator tests reject larger
deltas, additional changed pixels and resized images. `pngjs` 7.0.0 (MIT, locked
integrity) is a test-only PNG decoder, not a production or banking dependency.

The eight PDF wrapper tests also passed against the current production base image
in an isolated, network-disabled, read-only container with no production mounts.
Only Frappe imports/dependencies were real there; the PDF renderer and permission
checks were mocked by those unit tests. This is not a full PDF rendering proof.

Still open: production-image/site upgrade and rollback acceptance, broader account
and payment workflow regression, actual bank adapter delivery and approved bank
pilot. No production migration, bank contact or deployment occurred in this increment.

## Counter readiness regression, 13 September 2026

Run `34733021639` at `5e8d023` passed 86 native app tests but failed a cold
Workspace text comparison. Its canonical Zahlungsverkehr view contained all six
DocType count pills; the retained Page view was captured while those counts were
still arriving. The DOM snapshot and subsequent screenshot show different subsets
of completed counts. This is not evidence of a changed banking layout.

Frappe v16 `ShortcutWidget.set_actions()` starts `frappe.db.count(...).then(...)`
without making it part of EditorJS `isReady`. The browser test now additionally
waits for every rendered, configured DocType/List shortcut's nonempty count pill,
including zero. Single DocTypes, New, Page and Report shortcuts require no count.
Missing widgets or failed count requests still time out and fail the gate. Native
permission-filtered shortcut data determines which blocks should render.

Five Chromium regression tests cover delayed and absent/empty counts, zero,
non-counted shortcut types, wrong workspace, missing blocks/metadata and native
label matching. All five plus the existing 12 route/comparator tests pass locally.
The CI workflow runs the same checks before the native screenshot comparison.
Text, geometry, cold byte equality and the previous bounded warm rasterization
tolerance are unchanged; no region or count is masked. This change affects tests
only. The complete new CI run, including HRMS, remains required evidence.
