# AKB EBICS: transport-only submission and bank VEU

KT has selected **bank VEU only**, not a second ERP approval. On 29 September 2026,
AKB's live HTD response for EBICS user 1773 still reported authorisation level `E`
for BTU/MCT/CH/pain.001 version 09 on the CHF account ending 2002 and EUR account
ending 2003. An `E` upload may be executable without a separate bank approval.

The `ebics Connection.require_veu` switch must be enabled for `AKB CantoConnect
1773` after deploying this version. It rejects a payment before BTU unless the
bank's current HTD response contains **only `T`** for the exact debit IBAN and
payment BTF. It fails closed if the account, format or bank response is missing or
ambiguous. This switch cannot change a bank mandate: AKB must convert the user
to transport-only `T` and enable the intended approver(s) in its VEU application
for both accounts. Until then, EBICS payment uploads are deliberately blocked;
statement retrieval is unaffected.

The ERP records an upload attempt before contacting AKB. A timeout becomes
`Transmission uncertain` and must be reconciled with the bank before any new
submission. Successful BTU means `Awaiting bank VEU`, **not** bank acceptance,
approval, execution or debit. The proposal cannot be uploaded again automatically.
Only a verified bank response and bank booking can close the payment lifecycle.

The pre-VEU Kronoterm order `AAAC`, message ID
`MSG-20260929121625788170-951516D0f33239`, belongs to Payment Proposal
`0v2pp78s3s`. It was sent under the old `E` entitlement and must be marked
`Awaiting bank outcome (pre-VEU)` on production migration, with order/message
IDs filled, before the new send action is made available. Its HAC DS05 means
forwarded to postprocessing; it does not prove execution. Never resubmit it
without verifying AKB status and account debit.

Release checks: eight EBICS unit tests, including E rejection, exact-account T
matching and duplicate blocking; live read-only HTD check for both accounts;
DocType migration; field/status verification; active `require_veu=1` check;
negative send-path test **without** invoking BTU; unchanged bank statement sync.
