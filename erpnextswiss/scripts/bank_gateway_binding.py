"""Server-owned mapping of authenticated gateway originals to existing ERP accounts.

Internal integration only. This is not transport authentication or an HTTP API.
The caller must obtain the envelope and bytes through the trusted gateway channel.
"""

from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import json
import re

import frappe
from frappe.config import get_site_config

from erpnextswiss.scripts.bank_file_admission import BankFileError, MAX_ARCHIVE_BYTES
from erpnextswiss.scripts.bank_file_handover import receive_bank_archive, stage_bank_archive
from erpnextswiss.scripts.bank_matching_scope import BankMatchingScope


_OPAQUE = re.compile(r'[A-Za-z0-9_-]{1,100}\Z')
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_PROFILES = ('camt.053.001.08', 'camt.054.001.08')
_REQUEST_FIELDS = {'site', 'connection', 'participant', 'request', 'profile', 'from', 'until'}
_ENVELOPE_FIELDS = {'version', 'request', 'request_key', 'bank_id', 'segments', 'archive_sha256',
                    'archive_bytes', 'received_at', 'receipt_state'}


def _fail():
    raise BankFileError('Gateway source or server account binding is invalid or unavailable')


def _opaque(value):
    return isinstance(value, str) and _OPAQUE.fullmatch(value)


def _exact_date(value):
    if not isinstance(value, str):
        _fail()
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail()
    if parsed.isoformat() != value:
        _fail()
    return parsed


def _envelope(payload, metadata):
    if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_ARCHIVE_BYTES:
        _fail()
    if not isinstance(metadata, dict) or set(metadata) != _ENVELOPE_FIELDS:
        _fail()
    source = deepcopy(metadata)
    request = source['request']
    if type(source['version']) is not int or source['version'] != 1:
        _fail()
    if not isinstance(request, dict) or set(request) != _REQUEST_FIELDS:
        _fail()
    if any(not _opaque(request[key]) for key in ('site', 'connection', 'participant', 'request')):
        _fail()
    if request['profile'] not in _PROFILES:
        _fail()
    start, end = _exact_date(request['from']), _exact_date(request['until'])
    if not 0 <= (end - start).days <= 31:
        _fail()
    # ReadRequest::key uses these ASCII identities in the same JSON order.
    expected = sha256(json.dumps([request['site'], request['connection'], request['request']],
                                 separators=(',', ':')).encode()).hexdigest()
    if source['request_key'] != expected or not _opaque(source['bank_id']):
        _fail()
    if type(source['segments']) is not int or not 1 <= source['segments'] <= 64:
        _fail()
    if type(source['archive_bytes']) is not int or source['archive_bytes'] != len(payload):
        _fail()
    if (not isinstance(source['archive_sha256'], str) or not _HASH.fullmatch(source['archive_sha256'])
            or source['archive_sha256'] != sha256(payload).hexdigest()):
        _fail()
    if source['receipt_state'] not in ('unconfirmed', 'confirmed'):
        _fail()
    try:
        stamp = datetime.strptime(source['received_at'], '%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError):
        _fail()
    if stamp.strftime('%Y-%m-%dT%H:%M:%SZ') != source['received_at']:
        _fail()
    return source


def _binding(alias):
    frappe.only_for(('Accounts Manager', 'System Manager'))
    if not _opaque(alias):
        _fail()
    config = get_site_config(cached=False).get('bank_gateway_receive')
    if (not isinstance(config, dict) or set(config) != {'version', 'enabled', 'site', 'bindings'}
            or type(config['version']) is not int or config['version'] != 1
            or config['enabled'] is not True or config['site'] != frappe.local.site
            or not isinstance(config['bindings'], dict) or not 0 < len(config['bindings']) <= 64):
        _fail()
    binding = deepcopy(config['bindings'].get(alias))
    fields = {'gateway_site', 'gateway_connection', 'participant', 'connection', 'company', 'users', 'accounts'}
    if not isinstance(binding, dict) or set(binding) != fields:
        _fail()
    if any(not _opaque(binding[key]) for key in ('gateway_site', 'gateway_connection', 'participant')):
        _fail()
    if any(not isinstance(binding[key], str) or not binding[key].strip() for key in ('connection', 'company')):
        _fail()
    users = binding['users']
    if (not isinstance(users, list) or not 0 < len(users) <= 64
            or any(not isinstance(user, str) or not user.strip() or user == 'Guest' for user in users)
            or len(set(users)) != len(users) or frappe.session.user not in users):
        _fail()
    accounts = binding['accounts']
    if not isinstance(accounts, list) or not 0 < len(accounts) <= 64:
        _fail()
    for row in accounts:
        if not isinstance(row, dict) or set(row) != {'account', 'iban', 'currency'}:
            _fail()
        if (not isinstance(row['account'], str) or not row['account'].strip()
                or not isinstance(row['iban'], str) or not re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}', row['iban'])
                or row['currency'] not in ('CHF', 'EUR')):
            _fail()
    if len({row['account'] for row in accounts}) != len(accounts) or len({row['iban'] for row in accounts}) != len(accounts):
        _fail()
    owned_accounts = {row['account'] for row in accounts}
    identity = tuple(binding[key] for key in ('gateway_site', 'gateway_connection', 'participant'))
    for other_alias, other in config['bindings'].items():
        if other_alias == alias:
            continue
        if (not _opaque(other_alias) or not isinstance(other, dict)
                or not isinstance(other.get('accounts'), list)
                or any(not isinstance(row, dict) or not isinstance(row.get('account'), str) for row in other['accounts'])):
            _fail()
        if (other.get('connection') == binding['connection']
                or owned_accounts.intersection(row['account'] for row in other['accounts'])
                or tuple(other.get(key) for key in ('gateway_site', 'gateway_connection', 'participant')) == identity):
            _fail()
    return binding


def _prepare(payload, metadata, alias):
    binding = _binding(alias)
    source = _envelope(payload, metadata)
    request = source['request']
    if (request['site'], request['connection'], request['participant']) != (
            binding['gateway_site'], binding['gateway_connection'], binding['participant']):
        _fail()

    def validate(connection, *, for_update):
        # Recheck after every receiver retry and after commit. Do not turn a
        # configuration/permission change into an acknowledgement of another scope.
        if _binding(alias) != binding or connection.name != binding['connection'] or connection.company != binding['company']:
            _fail()
        connection.check_permission('write')
        if connection.enable_sync or connection.ebics_version != 'H005' or connection.scope != 'CH':
            _fail()
        for row in sorted(binding['accounts'], key=lambda value: value['account']):
            document = frappe.get_doc('Account', row['account'], for_update=for_update)
            document.check_permission('read')
            scope = BankMatchingScope(row['account'])
            if (scope.company != binding['company'] or scope.iban != row['iban'] or scope.currency != row['currency']
                    or document.company != binding['company']
                    or ''.join((document.get('iban') or '').split()).upper() != row['iban']
                    or document.account_currency != row['currency']):
                _fail()

    return {'profile': request['profile'], 'connection': binding['connection'],
            'accounts': [row['account'] for row in binding['accounts']],
            'source_reference': 'gateway:' + source['request_key'], '_validate_source': validate,
            '_source_metadata': json.dumps({key: value for key, value in source.items() if key != 'receipt_state'},
                                           sort_keys=True, separators=(',', ':'))}


def stage_gateway_archive(payload, metadata, *, binding):
    """Compose with an existing caller transaction; no implicit commit."""
    return stage_bank_archive(payload, **_prepare(payload, metadata, binding))


def receive_gateway_archive(payload, metadata, *, binding):
    """Dedicated committed ERP handover, still without HTTP or bank acknowledgement."""
    return receive_bank_archive(payload, **_prepare(payload, metadata, binding))
