# KT salary-slip print contract

The application owns **KT Lohnabrechnung** and the Salary Slip default Print
Format Property Setter on KT sites. `after_install` and `after_migrate` upsert
both idempotently. Sites without HRMS or KT Wärmesysteme AG are untouched.
No Frappe/HRMS core files or running-container source are patched. The packaged
HTML is the source of truth; edit it in Git, not the generated database record.

## Presentation and financial boundaries

- A4, KT logo from Company, compact employee/period block, aligned credit/debit
  columns, prominent net pay, separate employer information, repeating table
  headings and page numbers. The time summary shows approved Ferien attendance
  and recorded overtime for the slip period and year to date. Local
  Arial/Helvetica only; no external web fonts.
- The company phone field is deliberately not printed. No fabricated contact
  details, duplicate generic letterhead, workflow internals or full AHV number.
- All amounts come from the Salary Slip; no rates, PK split or wage calculation
  are changed. Rates are **not guessed** from today's Salary Structure because
  historical Salary Detail rows may not retain their original formula/basis.
- Net pay and a different rounded payout are distinct; Payroll Settings controls
  whether rounded_total is relevant. Zero rounded_total is not treated as missing.
- Draft/cancelled states are explicit. Submitted does not imply paid. Advances
  are not inferred from unrelated ledger entries or subtracted a second time.
- Third-party text is escaped. Employer contributions are information, not
  employee deductions. Only nonzero included earnings/deductions are itemized.
- Company/employee address data are current master data, as in native printing;
  payroll amounts remain the historical saved slip values.
- Time totals are read-only sums of submitted Attendance records through the
  slip end date. Ferien is limited to the `Ferien` leave type; half-days count
  as 0.5. Overtime is the saved `actual_overtime_duration` in hours for
  submitted Present attendance with an overtime type, matching HRMS's source
  records. If no submitted Attendance exists in a period, the summary says
  `Nicht erfasst` instead of implying zero. These are not leave balances,
  overtime pay, or proof of payment; no attendance or salary records are
  created or amended by printing.

The hierarchy is inspired by the public Abacus salary example (layout only, not
its 2018 rates): https://media.abacus.ch/abs/offertstandards/de/finanzprogramme/5-2-3.pdf
SwissSalary's public manual informed the separation of accounting date and payment
state: https://learn.swisssalary.ch/DE/SwissSalary-Gesamthandbuch/lohnabrechnung4.htm

## Verification and rollout

Run `python -m unittest discover -s tests -p 'test_salary_slip_print.py' -v`.
`scripts/preview_salary_slip.py` renders a candidate with native Frappe and
wkhtmltopdf in a read-only DB transaction. It selects the candidate only within
its own process; it never saves a Print Format or sends mail. Inspect normal and
long/multipage examples before activation. Keep real payroll previews private
and outside Git.

Deploy the committed app with the normal immutable-image workflow and migrate,
or apply the exact committed print-format data synchronizer as a targeted data
migration, then include that same commit in the next immutable image. A data-only
sync requires no app-container restart because the Jinja template is self-contained.
Never copy modified application code into a running container. Back up existing
Print Format / Salary Slip default Property Setters before changing them. Verify
the generated PDF, selected default and unchanged salary/ledger records afterward.

Rollback restores the prior Print Format/default from that backup. Revert the
source change as well, or the next migration deliberately reinstates the template.
Database default is site-wide; existing per-user print selections can still select
an older format until the user chooses KT Lohnabrechnung or resets that selection.
