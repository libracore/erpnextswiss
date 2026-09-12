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
  `frappe.re_route` extension point and the real `Workspaces/<name>` route.
  Aliases are registered only if that target is in the current user's allowed
  boot workspaces. No permission or workspace entry is invented or overwritten.
- The obsolete Page JSONs are removed from sync. Fresh installs do not create
  duplicate proxies. Existing app-owned proxies are renamed by native Frappe
  into `kt-swiss-route-<old-name>` before Workspace records are updated.
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

- Six isolated migration-contract tests and three Node route-registration tests
  pass locally. Existing inventory, artifact and Item maintenance tests remain
  part of the same run (20 isolated Python tests in total).
- Native Frappe tests cover fresh-install Workspace saves with route validation,
  a legacy upgrade with retained Version/comment/Custom Role/File/role records,
  technical Page assets, repeated upgrade calls and modified-proxy rejection.
  Their actual execution is a separate CI gate, not implied by isolated tests.
- Browser navigation, native full-app tests and production-image upgrade checks
  remain release gates. No production layout or banking configuration is changed
  by this source-only increment. Reconciliation and payment proposals remain
  existing workflows; no parallel payment UI is introduced.
