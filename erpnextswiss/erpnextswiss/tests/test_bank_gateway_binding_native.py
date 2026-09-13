"""Server-owned gateway mapping against real ERP documents and private originals."""

from copy import deepcopy
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

import frappe

from erpnextswiss.erpnextswiss.tests import test_bank_file_handover_native as fixtures
from erpnextswiss.scripts import bank_gateway_binding as gateway
from erpnextswiss.scripts import bank_file_handover as handover
from erpnextswiss.scripts.bank_file_admission import BankFileError
from erpnextswiss.erpnextswiss.tests.test_bank_file_admission import xml, zipped


def envelope(payload):
    request = {'site': 'ci-site', 'connection': 'ci-connection', 'participant': 'ci-participant',
               'request': 'ci-request', 'profile': 'camt.053.001.08', 'from': '2026-09-01', 'until': '2026-09-12'}
    return {'version': 1, 'request': request, 'request_key': sha256(json.dumps(
        [request['site'], request['connection'], request['request']], separators=(',', ':')).encode()).hexdigest(),
        'bank_id': 'CI-BANK', 'segments': 1, 'archive_sha256': sha256(payload).hexdigest(),
        'archive_bytes': len(payload), 'received_at': '2026-09-13T05:00:00Z', 'receipt_state': 'unconfirmed'}


def configuration(connection, company, account, user):
    return {'version': 1, 'enabled': True, 'site': frappe.local.site, 'bindings': {'ci': {
        'gateway_site': 'ci-site', 'gateway_connection': 'ci-connection', 'participant': 'ci-participant',
        'connection': connection, 'company': company, 'users': [user],
        'accounts': [{'account': account, 'iban': 'CH9300762011623852957', 'currency': 'CHF'}]}}}


class TestBankGatewayBindingNative(unittest.TestCase):
    row = fixtures.TestBankFileHandoverNative.row
    cleanup_rows = fixtures.TestBankFileHandoverNative.cleanup_rows
    manager = fixtures.TestBankFileHandoverNative.manager
    disk_files = fixtures.TestBankFileHandoverNative.disk_files

    def setUp(self):
        fixtures.TestBankFileHandoverNative.setUp(self)
        self.user = self.manager()
        frappe.set_user(self.user)
        self.config = configuration(self.connection, self.company_a, self.account_a, self.user)
        self.metadata = envelope(self.payload)
        self.scope = patch.dict(frappe.conf, bank_gateway_receive=self.config)
        self.scope.start()
        self.addCleanup(self.scope.stop)

    def stage(self, metadata=None):
        return gateway.stage_gateway_archive(self.payload, metadata or self.metadata, binding='ci')

    def test_server_mapping_persists_original_and_immutable_provenance_without_payment(self):
        before = self.disk_files()
        with patch.object(frappe.db, 'commit', side_effect=AssertionError('Caller owns commit')):
            result = self.stage()
        self.assertTrue(result['commit_required'])
        document = frappe.get_doc(handover.DOCTYPE, result['name'])
        self.assertEqual(document.company, self.company_a)
        self.assertEqual([row.account for row in document.accounts], [self.account_a])
        self.assertEqual(len(self.disk_files() - before), 1)
        self.assertEqual(handover._original(document), self.payload)
        metadata = json.loads(document.receipts[0].source_metadata)
        self.assertEqual(metadata['request'], self.metadata['request'])
        self.assertEqual(metadata['bank_id'], self.metadata['bank_id'])
        self.assertNotIn('receipt_state', metadata)
        self.assertTrue(self.stage()['replayed'])
        confirmed = deepcopy(self.metadata)
        confirmed['receipt_state'] = 'confirmed'
        self.assertTrue(self.stage(confirmed)['replayed'])

    def test_changed_dates_bank_identity_or_reception_time_cannot_rebind_the_same_source(self):
        first = self.stage()
        for key, value in (('bank_id', 'DIFFERENT'), ('segments', 2), ('received_at', '2026-09-13T06:00:00Z')):
            changed = deepcopy(self.metadata)
            changed[key] = value
            with self.assertRaises(BankFileError):
                self.stage(changed)
        changed = deepcopy(self.metadata)
        changed['request']['from'] = '2026-09-02'
        with self.assertRaises(BankFileError):
            self.stage(changed)
        self.assertEqual(len(frappe.get_doc(handover.DOCTYPE, first['name']).receipts), 1)

    def test_disabled_copied_unknown_or_foreign_user_configuration_never_reaches_storage(self):
        alternatives = [None, {}, {**self.config, 'enabled': False}, {**self.config, 'enabled': 1},
                        {**self.config, 'site': 'other-site'}, {**self.config, 'version': True}]
        altered = deepcopy(self.config)
        altered['bindings']['ci']['users'] = ['someone@example.invalid']
        alternatives.append(altered)
        with patch.object(gateway, 'stage_bank_archive', side_effect=AssertionError('No storage')):
            for value in alternatives:
                with patch.dict(frappe.conf, bank_gateway_receive=value), self.assertRaises(BankFileError):
                    self.stage()
            with self.assertRaises(BankFileError):
                gateway.stage_gateway_archive(self.payload, self.metadata, binding='unknown')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            self.stage()

    def test_untrusted_envelope_cannot_choose_accounts_site_connection_or_participant(self):
        alternatives = []
        for key in ('site', 'connection', 'participant'):
            changed = deepcopy(self.metadata)
            changed['request'][key] = 'other'
            request = changed['request']
            changed['request_key'] = sha256(json.dumps([request['site'], request['connection'], request['request']],
                                                       separators=(',', ':')).encode()).hexdigest()
            alternatives.append(changed)
        for key, value in (('accounts', [self.account_b]), ('version', True), ('segments', 65), ('archive_bytes', True),
                           ('archive_sha256', '0' * 64), ('receipt_state', 'approved'), ('received_at', 'yesterday')):
            alternatives.append({**self.metadata, key: value})
        for value in alternatives:
            with self.assertRaises(BankFileError):
                self.stage(value)
        self.assertEqual(frappe.db.count(handover.DOCTYPE, {'connection': self.connection}), 0)

    def test_current_account_and_connection_drift_fail_before_original_is_created(self):
        changes = [('Account', self.account_a, 'account_currency', 'EUR'),
                   ('Account', self.account_a, 'iban', 'CH5604835012345678009'),
                   ('Account', self.account_a, 'disabled', 1),
                   ('Account', self.account_a, 'company', self.company_b),
                   ('ebics Connection', self.connection, 'company', self.company_b),
                   ('ebics Connection', self.connection, 'ebics_version', 'H004'),
                   ('ebics Connection', self.connection, 'enable_sync', 1)]
        before = self.disk_files()
        for doctype, name, field, value in changes:
            previous = frappe.db.get_value(doctype, name, field)
            frappe.db.set_value(doctype, name, field, value)
            try:
                with self.assertRaises((BankFileError, frappe.ValidationError)):
                    self.stage()
            finally:
                frappe.db.set_value(doctype, name, field, previous)
        self.assertEqual(self.disk_files(), before)
        self.assertEqual(frappe.db.count(handover.DOCTYPE, {'connection': self.connection}), 0)

    def test_no_http_exposure_and_configuration_contains_no_payload_override(self):
        self.assertNotIn(gateway.receive_gateway_archive, frappe.whitelisted)
        self.assertNotIn(gateway.stage_gateway_archive, frappe.whitelisted)
        mapping = self.config['bindings']['ci']
        mapping['accounts'].append(dict(mapping['accounts'][0]))
        with self.assertRaises(BankFileError):
            self.stage()
        mapping['accounts'].pop()
        mapping['accounts'][0]['extra'] = 'not admitted'
        with self.assertRaises(BankFileError):
            self.stage()

    def test_both_profiles_and_currencies_use_the_explicit_current_account(self):
        for currency in ('CHF', 'EUR'):
            frappe.db.set_value('Account', self.account_a, 'account_currency', currency)
            self.config['bindings']['ci']['accounts'][0]['currency'] = currency
            for profile in ('camt.053.001.08', 'camt.054.001.08'):
                payload = zipped([('original.xml', xml(profile=profile, currency=currency, entries=True))])
                metadata = envelope(payload)
                metadata['request']['profile'] = profile
                metadata['request']['request'] = currency + '-' + profile.replace('.', '-')
                request = metadata['request']
                metadata['request_key'] = sha256(json.dumps([request['site'], request['connection'], request['request']],
                                                           separators=(',', ':')).encode()).hexdigest()
                result = gateway.stage_gateway_archive(payload, metadata, binding='ci')
                self.assertFalse(result['import_approved'])
                self.assertEqual(handover._original(frappe.get_doc(handover.DOCTYPE, result['name'])), payload)

    def test_mapping_change_between_preparation_and_locked_staging_is_rejected(self):
        prepared = gateway._prepare(self.payload, self.metadata, 'ci')
        self.config['bindings']['ci']['users'] = []
        with self.assertRaises(BankFileError):
            handover.stage_bank_archive(self.payload, **prepared)
        self.assertEqual(frappe.db.count(handover.DOCTYPE, {'connection': self.connection}), 0)
