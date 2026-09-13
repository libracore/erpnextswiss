"""Durable original-file handover to the existing read-only Bank Wizard.

Internal service functions, not HTTP endpoints or bank acknowledgement methods.
No ebics Statement parser, payment writer or automatic accounting is invoked.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import uuid4

import frappe

from erpnextswiss.scripts.bank_camt_preview import preview_camt_archive
from erpnextswiss.scripts.bank_file_admission import BankFileError, MAX_ARCHIVE_BYTES
from erpnextswiss.scripts.bank_matching_scope import BankMatchingScope


DOCTYPE = 'Bank File Handover'
_controlled_write = ContextVar('bank_file_handover_write', default=False)
_SOURCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
MAX_RECEIPTS = 1024


class BankOriginalFileMixin:
    """Use the v16 extension point; unrelated File behavior stays native."""

    def is_downloadable(self):
        # Native private-file downloads bypass the has_permission hook and use
        # this method, whose base implementation alone admits a revoked owner.
        return file_has_permission(self) and super().is_downloadable()

    def get_content(self, encodings=None):
        if self.attached_to_doctype == DOCTYPE:
            if not file_has_permission(self):
                frappe.throw('Bank original is outside the current account scope', frappe.PermissionError)
            # Some valid ZIP bytes also decode as UTF-16. Native File then writes
            # that text as UTF-8 during insertion, corrupting the bank original.
            return super().get_content(encodings=[])
        return super().get_content(encodings=encodings)

    def before_insert(self):
        guard_file_mutation(self)
        return super().before_insert()

    def validate(self):
        guard_file_mutation(self)
        return super().validate()

    def on_trash(self):
        guard_file_mutation(self)
        return super().on_trash()


def _digest(values):
    return sha256(json.dumps(values, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


@contextmanager
def _transaction():
    """Rollback file callbacks too if a caller catches an error and then commits."""
    from frappe.utils import CallbackManager

    savepoint = 'bank_handover_' + uuid4().hex
    names = ('before_commit', 'after_commit', 'before_rollback', 'after_rollback')
    original = {name: getattr(frappe.db, name) for name in names}
    local = {name: CallbackManager() for name in names}
    previous_control = frappe.db._disable_transaction_control
    frappe.db.savepoint(savepoint)
    for name, manager in local.items():
        setattr(frappe.db, name, manager)
    frappe.db._disable_transaction_control = True
    token = _controlled_write.set(True)
    succeeded, aborted = False, False
    try:
        yield
        succeeded = True
    except frappe.QueryDeadlockError:
        aborted = True
        raise
    finally:
        try:
            if succeeded:
                for name in names:
                    original[name].add(local[name].run)
            else:
                try:
                    local['before_rollback'].run()
                finally:
                    if not aborted:
                        frappe.db.rollback(save_point=savepoint)
                    local['after_rollback'].run()
        finally:
            _controlled_write.reset(token)
            for name, manager in original.items():
                setattr(frappe.db, name, manager)
            frappe.db._disable_transaction_control = previous_control
            if aborted:
                # InnoDB deadlocks roll back the outer transaction as well.
                frappe.db._disable_transaction_control = False
                try:
                    frappe.db.rollback()
                finally:
                    frappe.db._disable_transaction_control = previous_control
            else:
                frappe.db.release_savepoint(savepoint)


def _accounts(document):
    accounts = [row.account for row in document.accounts]
    if not accounts or len(accounts) > 64 or len(set(accounts)) != len(accounts):
        raise BankFileError('Bank handover account binding is invalid')
    for account in accounts:
        scope = BankMatchingScope(account)
        if scope.company != document.company:
            raise BankFileError('Bank handover company binding changed')
    expected = 'BFH-' + _digest([document.connection, document.company, sorted(accounts),
                                document.profile, document.archive_sha256])
    if document.name != expected or document.handover_key != expected:
        raise BankFileError('Bank handover identity binding changed')
    return accounts


def _check_connection(document):
    connection = frappe.get_doc('ebics Connection', document.connection)
    connection.check_permission('read')
    if connection.company != document.company or connection.enable_sync:
        raise BankFileError('Bank handover connection changed or legacy synchronization is enabled')
    return connection


def has_permission(doc, ptype='read', user=None):
    if user and user != frappe.session.user:
        # Do not evaluate another user's scope using the caller's cached identity.
        return False
    if ptype not in ('read', 'select', 'report'):
        return False
    try:
        _accounts(doc)
        _check_connection(doc)
    except (frappe.PermissionError, frappe.DoesNotExistError, frappe.ValidationError, BankFileError):
        return False
    return True


def file_has_permission(doc, ptype='read', user=None):
    if doc.attached_to_doctype != DOCTYPE:
        return True  # A restricting hook must not deny unrelated existing Files.
    if ptype not in ('read', 'select') or not doc.is_private:
        return False
    try:
        parent = frappe.get_doc(DOCTYPE, doc.attached_to_name)
    except frappe.DoesNotExistError:
        return False
    return has_permission(parent, ptype, user)


def permission_query_conditions(user=None):
    if user and user != frappe.session.user:
        return '1=0'
    if not set(frappe.get_roles()).intersection(('Accounts User', 'Accounts Manager', 'System Manager')):
        return '1=0'
    try:
        accounts = frappe.get_list('Account', filters={'account_type': 'Bank', 'disabled': 0, 'is_group': 0},
                                   pluck='name', limit_page_length=0)
        connections = frappe.get_list('ebics Connection', filters={'enable_sync': 0},
                                      fields=['name', 'company'], limit_page_length=0)
        companies = frappe.get_list('Company', pluck='name', limit_page_length=0)
    except frappe.PermissionError:
        return '1=0'
    connections = [row for row in connections if row.company in companies]
    if not accounts or not connections:
        return '1=0'
    allowed = ','.join(frappe.db.escape(account) for account in accounts)
    bindings = ' OR '.join('(h.connection={0} AND h.company={1})'.format(
        frappe.db.escape(row.name), frappe.db.escape(row.company)) for row in connections)
    # Every account, not merely one child row, must still be authorized.
    return ("EXISTS (SELECT 1 FROM `tabBank File Handover` h WHERE h.name=`tabBank File Handover`.name "
            "AND (" + bindings + ")) AND EXISTS (SELECT 1 FROM `tabBank Handover Account` a "
            "WHERE a.parent=`tabBank File Handover`.name AND a.parenttype='Bank File Handover') "
            "AND NOT EXISTS (SELECT 1 FROM `tabBank Handover Account` a "
            "WHERE a.parent=`tabBank File Handover`.name AND a.parenttype='Bank File Handover' "
            "AND (a.account IS NULL OR a.account NOT IN (" + allowed + ") OR NOT EXISTS (SELECT 1 FROM `tabAccount` bank "
            "WHERE bank.name=a.account AND bank.company=`tabBank File Handover`.company)))")


def file_permission_query_conditions(user=None):
    unrelated = "(`tabFile`.attached_to_doctype IS NULL OR `tabFile`.attached_to_doctype!='Bank File Handover')"
    # File queries also run while this app's DocTypes are first being installed.
    if not all(frappe.db.table_exists(name) for name in (DOCTYPE, 'Bank Handover Account')):
        return unrelated
    condition = permission_query_conditions(user)
    return ('(' + unrelated +
            "OR (`tabFile`.is_private=1 AND `tabFile`.attached_to_name IN "
            "(SELECT name FROM `tabBank File Handover` WHERE " + condition + ')))')


def guard_file_mutation(doc, method=None):
    """Retain original attachment binding, including copies of its private URL."""
    previous = None if doc.is_new() else frappe.db.get_value('File', doc.name, 'attached_to_doctype')
    protected = doc.attached_to_doctype == DOCTYPE or previous == DOCTYPE
    if not protected and (doc.file_url or '').startswith('/private/files/'):
        protected = bool(frappe.db.exists('File', {'file_url': doc.file_url, 'attached_to_doctype': DOCTYPE}))
    if not protected:
        return
    if _controlled_write.get() and doc.is_new() and doc.attached_to_doctype == DOCTYPE and doc.is_private:
        return
    frappe.throw('Bank originals cannot be changed, detached or copied through generic File operations',
                 frappe.PermissionError)


def _original(document):
    if not isinstance(document.byte_count, int) or not 0 < document.byte_count <= MAX_ARCHIVE_BYTES:
        raise BankFileError('Bank handover original size is invalid')
    source = frappe.get_doc('File', document.original_file)
    source.check_permission('read')
    if (not source.is_private or source.attached_to_doctype != DOCTYPE
            or source.attached_to_name != document.name
            or not (source.file_url or '').startswith('/private/files/')):
        raise BankFileError('Bank handover original binding is invalid')
    private = Path(frappe.get_site_path('private', 'files')).resolve()
    path = Path(source.get_full_path())
    if path.is_symlink() or not path.resolve().is_relative_to(private):
        raise BankFileError('Bank handover original path is invalid')
    with path.open('rb') as stream:
        content = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) != document.byte_count or sha256(content).hexdigest() != document.archive_sha256:
        raise BankFileError('Bank handover original integrity check failed')
    return content


def get_handover_preview(name):
    """Re-read original bytes and CURRENT permissions/matches, not a stored approval."""
    document = frappe.get_doc(DOCTYPE, name)
    document.check_permission('read')
    _check_connection(document)
    accounts = _accounts(document)
    return preview_camt_archive(_original(document), document.profile,
                                company=document.company, accounts=accounts)


def stage_bank_archive(payload, profile, *, connection, accounts, source_reference):
    """Stage atomically; the caller must commit before acknowledging ERP durability.

    Explicit account lists are an internal adapter input, not proof of a bank
    contract. A future authenticated gateway binding must supply them server-side.
    Source/content identity does not certify cross-file business deduplication.
    """
    frappe.only_for(('Accounts Manager', 'System Manager'))
    if not isinstance(source_reference, str) or not _SOURCE.fullmatch(source_reference):
        raise BankFileError('An opaque source reference is required')
    if (not isinstance(accounts, (list, tuple)) or not 0 < len(accounts) <= 64
            or any(not isinstance(account, str) or not account.strip() for account in accounts)
            or len(set(accounts)) != len(accounts)):
        raise BankFileError('Explicit unique bank accounts are required')
    accounts = sorted(accounts)
    with _transaction():
        # One serialized receipt stream per existing connection, including callers
        # that use different request IDs for identical original bytes.
        connection_doc = frappe.get_doc('ebics Connection', connection, for_update=True)
        connection_doc.check_permission('write')
        if connection_doc.enable_sync:
            raise BankFileError('Legacy synchronization must be disabled for this handover')
        company = connection_doc.company
        preview = preview_camt_archive(payload, profile, company=company, accounts=accounts)
        archive = preview['archive']
        content_key = _digest([connection_doc.name, company, accounts, profile, archive.sha256])
        receipt_key = _digest([connection_doc.name, source_reference])
        name = 'BFH-' + content_key
        previous = frappe.db.get_value('Bank Handover Receipt', {'receipt_key': receipt_key}, 'parent')
        if previous and previous != name:
            raise BankFileError('The source reference is already bound to different bank data')
        if frappe.db.exists(DOCTYPE, name):
            document = frappe.get_doc(DOCTYPE, name, for_update=True)
            document.check_permission('read')
            if _original(document) != payload:
                raise BankFileError('Bank handover original differs from the received bytes')
        else:
            document = frappe.get_doc({
                'doctype': DOCTYPE, 'handover_key': name, 'company': company, 'connection': connection_doc.name,
                'profile': profile, 'status': 'Staged', 'archive_sha256': archive.sha256,
                'byte_count': len(payload), 'accounts': [{'account': account} for account in accounts],
                'statement_count': len(preview['statements']),
                'entry_count': sum(len(s['entries']) for s in preview['statements']),
            })
            document.insert(ignore_permissions=True)
            from frappe.utils.file_manager import save_file
            original = save_file(name + '.zip', payload, DOCTYPE, name, is_private=1)
            document.original_file = original.name
            # Verify the actual stored binary object, not just File metadata.
            if _original(document) != payload:
                raise BankFileError('Bank handover original failed readback')
        if not previous:
            if len(document.receipts) >= MAX_RECEIPTS:
                raise BankFileError('Bank handover receipt limit reached')
            document.append('receipts', {'receipt_key': receipt_key, 'source_reference': source_reference,
                                          'received_by': frappe.session.user, 'received_at': frappe.utils.now_datetime()})
            document.save(ignore_permissions=True)
        return {'name': document.name, 'archive_sha256': document.archive_sha256,
                'status': 'Staged', 'receipt_count': len(document.receipts),
                'replayed': bool(previous), 'commit_required': True, 'import_approved': False}
