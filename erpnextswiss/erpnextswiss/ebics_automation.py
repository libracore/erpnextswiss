"""Fail-closed EBICS 3.0 retrieval with a durable bank receipt.

The old statement importer acknowledges before persistence and may submit a
Payment Entry while downloading. This module never calls that importer.
"""

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
import re
from zipfile import ZIP_STORED, ZipFile

import frappe
from frappe.config import get_site_config

from erpnextswiss.scripts.bank_camt_preview import preview_camt_archive
from erpnextswiss.scripts.bank_file_admission import BankFileError, MAX_FILE_BYTES, MAX_TOTAL_BYTES


PROFILE = "camt.053.001.08"
STATEMENT_PROFILES = {"04": "camt.053.001.04", "08": PROFILE}
MAX_DOWNLOADS_PER_RUN = 14
MAX_ARCHIVED_DOWNLOADS = 10000
_TRANSACTION_ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
_RECEIPT_NAME = re.compile(r"statement-[0-9]{3}\.xml\Z")


def _archive_bytes(data):
    """Store SDK-delivered XML as bounded UTF-8 in a deterministic envelope."""
    if not isinstance(data, dict) or len(data) > 64:
        raise BankFileError("EBICS delivered an invalid file set")
    files = {}
    total = 0
    for index, (source, content) in enumerate(sorted(data.items(), key=lambda item: str(item[0]))):
        if not isinstance(source, str) or not source or not isinstance(content, (bytes, str)):
            raise BankFileError("EBICS delivered an invalid file")
        raw = content.encode("utf-8") if isinstance(content, str) else content
        if not 0 < len(raw) <= MAX_FILE_BYTES:
            raise BankFileError("EBICS XML exceeds the configured file limit")
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise BankFileError("EBICS XML exceeds the configured transfer limit")
        # The bank-provided name is metadata only; it never becomes a path.
        files[f"statement-{index:03d}.xml"] = raw.decode("utf-8")
    encoded = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_TOTAL_BYTES + 4096:
        raise BankFileError("EBICS receipt exceeds the storage limit")
    return encoded


def _receipt_files(payload):
    files = json.loads(payload)
    if not isinstance(files, dict) or len(files) > 64:
        raise BankFileError("Stored EBICS receipt is invalid")
    result = {}
    total = 0
    for name, content in sorted(files.items()):
        if not _RECEIPT_NAME.fullmatch(name) or not isinstance(content, str):
            raise BankFileError("Stored EBICS receipt is invalid")
        raw = content.encode("utf-8")
        total += len(raw)
        if not 0 < len(raw) <= MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise BankFileError("Stored EBICS receipt exceeds file limits")
        result[name] = (raw, sha256(raw).hexdigest())
    return result


def _zip_from_receipt(payload, included_hashes=None):
    files = _receipt_files(payload)
    if not files:
        return None
    output = BytesIO()
    included = set(included_hashes) if included_hashes is not None else None
    emitted = set()
    with ZipFile(output, "w", compression=ZIP_STORED, allowZip64=False) as archive:
        for name, (raw, digest) in files.items():
            if included is not None and (digest not in included or digest in emitted):
                continue
            archive.writestr(name, raw)
            emitted.add(digest)
    if not emitted:
        return None
    return output.getvalue()


def _accounts(connection):
    config = get_site_config(cached=False).get("ebics_auto_accounts")
    if (not isinstance(config, dict) or set(config) != {"version", "bindings"}
            or config["version"] != 1 or not isinstance(config["bindings"], dict)):
        raise BankFileError("Explicit EBICS account binding is not configured")
    accounts = config["bindings"].get(connection.name)
    if (not isinstance(accounts, list) or not 0 < len(accounts) <= 64
            or any(not isinstance(value, str) or not value for value in accounts)
            or len(set(accounts)) != len(accounts)):
        raise BankFileError("No bounded EBICS account binding is available")
    for name in accounts:
        account = frappe.get_doc("Account", name)
        if (account.company != connection.company or account.account_type != "Bank"
                or account.disabled or account.is_group or not account.iban
                or account.account_currency not in ("CHF", "EUR")):
            raise BankFileError("EBICS account binding no longer matches the ledger")
    return accounts


def _statement_profile(connection):
    version = connection.statement_btf_version
    if connection.scope != "CH" or version not in STATEMENT_PROFILES:
        raise BankFileError("EBICS connection is not configured for a supported Swiss statement profile")
    return STATEMENT_PROFILES[version]


def _preview(payload, connection, included_hashes=None, profile=None):
    archive = _zip_from_receipt(payload, included_hashes=included_hashes)
    if archive is None:
        return {"statements": []}
    return preview_camt_archive(archive, profile or _statement_profile(connection),
                                company=connection.company, accounts=_accounts(connection))


def _receipt_key(connection_name, transaction_id):
    digest = sha256(json.dumps([connection_name, transaction_id], separators=(",", ":")).encode()).hexdigest()
    return "EBICS-" + digest


def _verify_receipt(record):
    payload = record.payload_json.encode("utf-8")
    if len(payload) != record.payload_bytes or sha256(payload).hexdigest() != record.payload_sha256:
        raise BankFileError("Stored EBICS receipt failed integrity verification")
    return payload


def _known_files(connection):
    """Build the first-seen per-file index, including legacy single-file receipts."""
    known = {}
    offset = 0
    while offset < MAX_ARCHIVED_DOWNLOADS:
        names = frappe.get_all("EBICS Download", filters={"connection": connection.name,
                                                        "ack_state": "Confirmed"},
                               pluck="name", order_by="creation asc, name asc",
                               limit_start=offset, limit_page_length=100)
        for name in names:
            record = frappe.get_doc("EBICS Download", name)
            for _, digest in _receipt_files(_verify_receipt(record)).values():
                known.setdefault(digest, name)
        if len(names) < 100:
            return known
        offset += len(names)
    raise BankFileError("EBICS archive requires indexed review before further downloads")


def _classify_files(payload, known_files):
    hashes = list(dict.fromkeys(digest for _, digest in _receipt_files(payload).values()))
    duplicate_sources = {digest: known_files[digest] for digest in hashes if digest in known_files}
    new_hashes = [digest for digest in hashes if digest not in known_files]
    sources = set(duplicate_sources.values())
    return {
        "file_hashes_json": json.dumps(hashes),
        "new_file_hashes_json": json.dumps(new_hashes),
        "duplicate_sources_json": json.dumps(duplicate_sources, sort_keys=True),
        "duplicate_of": next(iter(sources)) if not new_hashes and len(sources) == 1 else None,
    }, new_hashes


def _acknowledge(connection, record, client=None):
    if record.ack_state == "Confirmed":
        return
    _verify_receipt(record)
    # The bank reply is sent only after a completed ERP commit and readback.
    (client or connection.get_client()).confirm_download(trans_id=record.bank_transaction_id)
    record.db_set("ack_state", "Confirmed", commit=True)


def _pending_receipt(connection):
    names = frappe.get_all("EBICS Download", filters={"connection": connection.name, "ack_state": "Pending"},
                           pluck="name", order_by="creation asc", limit_page_length=2)
    if len(names) > 1:
        raise BankFileError("Multiple unacknowledged EBICS downloads require review")
    return frappe.get_doc("EBICS Download", names[0]) if names else None


def _download_pending(connection, requested_date, known_files=None):
    """Fetch one bank-provided current file set, never a historical DateRange.

    requested_date is the ERP retrieval date for audit, not a filter sent to the
    bank. The bank may provide several files for the same day, so it is not a
    uniqueness key; the EBICS transaction ID is.
    """
    pending = _pending_receipt(connection)
    if pending:
        _acknowledge(connection, pending)
        return pending

    from fintech.ebics import BusinessTransactionFormat

    profile = _statement_profile(connection)
    client = connection.get_client()
    btf = BusinessTransactionFormat(service="EOP", msg_name="camt.053", scope="CH", container="ZIP",
                                    version=connection.statement_btf_version)
    try:
        data = client.BTD(btf)
    except Exception as error:
        if str(error) == "EBICS_NO_DOWNLOAD_DATA_AVAILABLE":
            return None
        raise

    transaction_id = client.last_trans_id
    if not isinstance(transaction_id, str) or not _TRANSACTION_ID.fullmatch(transaction_id):
        raise BankFileError("EBICS did not supply a safe receipt transaction ID")
    payload = _archive_bytes(data)
    _preview(payload, connection, profile=profile)  # Validate every file/account before positive bank receipt.
    name = _receipt_key(connection.name, transaction_id)
    if frappe.db.exists("EBICS Download", name):
        raise BankFileError("EBICS transaction identity is already archived")
    if known_files is None:
        known_files = _known_files(connection)
    file_metadata, new_hashes = _classify_files(payload, known_files)
    record = frappe.get_doc({
        "doctype": "EBICS Download", "download_key": name, "connection": connection.name,
        "company": connection.company, "requested_date": requested_date.isoformat(),
        "profile": profile, "bank_transaction_id": transaction_id, "ack_state": "Pending",
        "processing_state": "Duplicate" if not new_hashes else "Pending", **file_metadata,
        "payload_sha256": sha256(payload).hexdigest(),
        "payload_bytes": len(payload), "payload_json": payload.decode("utf-8"),
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    _verify_receipt(frappe.get_doc("EBICS Download", record.name))
    _acknowledge(connection, record, client=client)
    for digest in new_hashes:
        known_files[digest] = record.name
    return record


def _money(value):
    try:
        amount = Decimal(str(value))
        rounded = amount.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount > 0 and amount == rounded else None


def _reference_mentions(value, text):
    if not isinstance(value, str) or not value or not isinstance(text, str):
        return False
    return bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(value) + r"(?![A-Za-z0-9])", text))


def _strict_invoice_candidate(connection, statement, entry):
    """Return one live invoice only when bank, matcher and ledger all agree."""
    if (statement["balance_check"] != "matched" or entry["issues"]
            or entry["detail_count"] > 1 or len(entry["candidates"]) != 1):
        return None
    candidate = entry["candidates"][0]
    amount = _money(entry["amount"])
    if (amount is None or amount != _money(candidate.get("amount"))
            or candidate.get("currency") != statement["currency"]
            or candidate.get("credit_debit") != entry["credit_debit"]
            or candidate.get("date") != (entry["booking_date"] or "")[:10]
            or amount != _money(candidate.get("matched_amount"))):
        return None
    bank_reference = candidate.get("unique_reference")
    if (not isinstance(bank_reference, str) or not bank_reference.strip()
            or bank_reference not in {entry.get("reference"), entry.get("entry_reference")}):
        return None
    direction = candidate["credit_debit"]
    if direction not in ("CRDT", "DBIT") or candidate.get("expense_matches"):
        return None
    names = candidate.get("invoice_matches")
    if not isinstance(names, list) or len(names) != 1 or not isinstance(names[0], str):
        return None
    doctype = "Sales Invoice" if direction == "CRDT" else "Purchase Invoice"
    invoice = frappe.get_doc(doctype, names[0])
    party_field = "customer" if direction == "CRDT" else "supplier"
    if (invoice.docstatus != 1 or invoice.company != connection.company
            or invoice.get(party_field) != candidate.get("party_match")
            or _money(invoice.outstanding_amount) != amount
            or invoice.currency != statement["currency"]):
        return None
    reference_text = candidate.get("transaction_reference") or ""
    accepted = {str(invoice.name)}
    accepted.update(str(value) for value in (invoice.get("bill_no"), invoice.get("esr_reference"),
                                             invoice.get("esr_reference_number"),
                                             invoice.get("reference_number_full"))
                    if value and len(str(value)) >= 6)
    if not any(_reference_mentions(value, reference_text) for value in accepted):
        return None
    return candidate, doctype, invoice, amount


def _book_exact_match(connection, statement, entry, download_name):
    matched = _strict_invoice_candidate(connection, statement, entry)
    if matched is None:
        return False
    candidate, doctype, invoice, amount = matched
    reference = candidate["unique_reference"]
    if frappe.db.exists("Payment Entry", {"company": connection.company, "reference_no": reference,
                                           "docstatus": ("<", 2)}):
        return False

    from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import get_default_accounts, make_payment_entry

    defaults = get_default_accounts(company=connection.company)
    incoming = candidate["credit_debit"] == "CRDT"
    payload = {
        "amount": float(amount), "date": candidate["date"], "reference_no": reference,
        "paid_from": defaults.get("receivable_account") if incoming else statement["account"],
        "paid_to": statement["account"] if incoming else defaults.get("payable_account"),
        "type": "Receive" if incoming else "Pay", "party_type": "Customer" if incoming else "Supplier",
        "party": candidate["party_match"], "references": repr([invoice.name]),
        "remarks": "EBICS {0}; {1}".format(download_name, candidate.get("transaction_reference") or ""),
        "auto_submit": False, "party_iban": candidate.get("party_iban"),
        "company": connection.company,
    }
    savepoint = "ebics_booking_" + sha256(reference.encode()).hexdigest()[:20]
    frappe.db.savepoint(savepoint)
    try:
        result = make_payment_entry(**payload)
        payment = frappe.get_doc("Payment Entry", result["payment_entry"])
        references = payment.references or []
        if (payment.docstatus != 0 or payment.company != connection.company
                or payment.party != candidate["party_match"]
                or _money(payment.paid_amount) != amount
                or _money(payment.received_amount) != amount
                or Decimal(str(payment.difference_amount or 0)) != 0
                or Decimal(str(payment.unallocated_amount or 0)) != 0
                or payment.deductions or len(references) != 1
                or references[0].reference_doctype != doctype
                or references[0].reference_name != invoice.name
                or _money(references[0].allocated_amount) != amount):
            raise BankFileError("Candidate payment differs from the confirmed bank and invoice amount")
        payment.submit()
        frappe.db.commit()
        return True
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise


def _process_download(connection, record):
    if record.ack_state != "Confirmed":
        raise BankFileError("Bank receipt must be confirmed before automatic booking")
    payload = _verify_receipt(record)
    if record.new_file_hashes_json:
        new_hashes = json.loads(record.new_file_hashes_json)
        if (not isinstance(new_hashes, list) or any(not isinstance(item, str) for item in new_hashes)
                or len(new_hashes) > 64):
            raise BankFileError("EBICS new-file metadata is invalid")
    else:
        # Old receipts predate per-file metadata. They are only replayed after
        # their durable bank receipt; the ledger reference guard still applies.
        new_hashes = list(dict.fromkeys(digest for _, digest in _receipt_files(payload).values()))
    if not new_hashes:
        record.db_set("processing_state", "Duplicate", commit=True)
        return {"booked": 0, "review": 0}
    preview = _preview(payload, connection, included_hashes=new_hashes, profile=record.profile)
    booked = review = 0
    for statement in preview["statements"]:
        for entry in statement["entries"]:
            try:
                if _book_exact_match(connection, statement, entry, record.name):
                    booked += 1
                else:
                    review += 1
            except Exception as error:
                # An isolated candidate is never allowed to book a difference or
                # block archiving the other bank entries. It stays visible for review.
                review += 1
                frappe.log_error(title="EBICS candidate requires review", message=type(error).__name__)
    record.db_set({"booked_count": booked, "review_count": review,
                   "processing_state": "Review" if review else "Completed"}, commit=True)
    return {"booked": booked, "review": review}


def sync_connection(connection_name, debug=False):
    """Drain current pending bank files, with durable receipts and no payments."""
    lock = frappe.cache().lock("ebics-download:" + connection_name, timeout=300, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return {"status": "already_running"}
    try:
        connection = frappe.get_doc("ebics Connection", connection_name)
        if not connection.enable_sync or not connection.activated or connection.ebics_version != "H005":
            return {"status": "disabled"}
        _statement_profile(connection)
        waiting = frappe.get_all("EBICS Download", filters={"connection": connection.name,
                                                          "ack_state": "Confirmed", "processing_state": "Pending"},
                                 pluck="name", order_by="creation asc", limit_page_length=100)
        for name in waiting:
            _process_download(connection, frappe.get_doc("EBICS Download", name))
        repeated_payloads = set()
        duplicates = 0
        pending = _pending_receipt(connection)
        if pending:
            # Resolve an interrupted bank acknowledgement before any other BTD.
            resumed = _download_pending(connection, frappe.utils.getdate(pending.requested_date))
            if resumed.processing_state == "Pending":
                _process_download(connection, resumed)
            elif resumed.processing_state == "Duplicate":
                repeated_payloads.add(resumed.payload_sha256)
                duplicates += 1
        known_files = _known_files(connection)
        # Each BTD without a date filter returns a bank-pending file set. Keep
        # fetching until the bank reports no data, but bound each scheduler run.
        # The request date is audit metadata only, never a file/date cursor.
        fetched = 0
        exhausted = True
        for _ in range(MAX_DOWNLOADS_PER_RUN):
            record = _download_pending(connection, frappe.utils.getdate(), known_files)
            if record is None:
                exhausted = False
                break
            if record.processing_state == "Duplicate":
                duplicates += 1
                if record.payload_sha256 in repeated_payloads:
                    return {"status": "repeated_duplicate", "downloads_fetched": fetched,
                            "duplicate_receipts": duplicates}
                repeated_payloads.add(record.payload_sha256)
                continue
            _process_download(connection, record)
            fetched += 1
        result = {"status": "limit_reached" if exhausted else "ok", "downloads_fetched": fetched}
        if duplicates:
            result["duplicate_receipts"] = duplicates
        return result
    finally:
        lock.release()


def reconcile_historical_receipts(connection_name, apply=False):
    """Audit and optionally mark old repeated receipts; never delete bank data.

    Default is read-only. An explicit boolean True updates only deduplication
    metadata/status after validating every archived receipt in chronological
    order. Existing booked entries are never silently reclassified.
    """
    if type(apply) is not bool:
        raise ValueError("apply must be a boolean")
    lock = frappe.cache().lock("ebics-download:" + connection_name, timeout=300, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        return {"status": "already_running"}
    try:
        connection = frappe.get_doc("ebics Connection", connection_name)
        known_files = {}
        changed = duplicate = 0
        offset = 0
        while offset < MAX_ARCHIVED_DOWNLOADS:
            names = frappe.get_all("EBICS Download", filters={"connection": connection.name,
                                                            "profile": PROFILE, "ack_state": "Confirmed"},
                                   pluck="name", order_by="creation asc, name asc",
                                   limit_start=offset, limit_page_length=100)
            for name in names:
                record = frappe.get_doc("EBICS Download", name)
                metadata, new_hashes = _classify_files(_verify_receipt(record), known_files)
                if not new_hashes:
                    if int(record.booked_count or 0):
                        raise BankFileError("Historical duplicate with booked entries requires manual review")
                    duplicate += 1
                    target_state = "Duplicate"
                else:
                    if record.processing_state == "Duplicate":
                        raise BankFileError("A unique historical receipt is marked duplicate")
                    target_state = record.processing_state
                updates = {key: value for key, value in metadata.items() if record.get(key) != value}
                if record.processing_state != target_state:
                    updates["processing_state"] = target_state
                if updates:
                    changed += 1
                    if apply is True:
                        record.db_set(updates, commit=False)
                for digest in new_hashes:
                    known_files[digest] = name
            if len(names) < 100:
                if apply is True:
                    frappe.db.commit()
                return {"status": "applied" if apply is True else "dry_run",
                        "receipts_checked": offset + len(names), "receipts_changed": changed,
                        "duplicate_receipts": duplicate}
            offset += len(names)
        raise BankFileError("EBICS archive exceeds safe reconciliation limit")
    except Exception:
        if apply is True:
            frappe.db.rollback()
        raise
    finally:
        lock.release()


def sync(debug=False):
    for row in frappe.get_all("ebics Connection", filters={"enable_sync": 1}, pluck="name"):
        try:
            result = sync_connection(row, debug=debug)
            if result.get("status") in ("limit_reached", "repeated_duplicate"):
                frappe.log_error(title="EBICS retrieval needs bank review",
                                 message="Connection {0}: {1}; downloads {2}, duplicates {3}".format(
                                     row, result["status"], result.get("downloads_fetched", 0),
                                     result.get("duplicate_receipts", 0)))
        except Exception as error:
            frappe.log_error(title="EBICS retrieval failed", message=type(error).__name__)
