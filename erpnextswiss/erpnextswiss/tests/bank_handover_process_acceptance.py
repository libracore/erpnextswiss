"""Independent-process acceptance, restricted to the disposable CI test site."""

from io import BytesIO
import json
import os
from pathlib import Path
import time
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

import frappe

from erpnextswiss.erpnextswiss.tests.test_bank_file_admission import PROFILE, xml
from erpnextswiss.scripts import bank_file_handover as handover


COMPANY = 'KT-HANDOVER-CI-COMPANY'
ACCOUNT = 'KT-HANDOVER-CI-ACCOUNT'
CONNECTION = 'KT-HANDOVER-CI-CONNECTION'
FINANCIAL = ('GL Entry', 'Payment Entry', 'Bank Transaction', 'Sales Invoice', 'Purchase Invoice')


def _guard():
    if os.environ.get('CI') != 'true' or frappe.local.site != 'test_site' or not frappe.conf.allow_tests:
        raise RuntimeError('Bank handover acceptance is restricted to disposable CI test_site')
    frappe.set_user('Administrator')


def _payload(marker='original'):
    data = BytesIO()
    with ZipFile(data, 'w') as archive:
        archive.writestr(ZipInfo('statement.xml', date_time=(2026, 9, 12, 0, 0, 0)),
                         xml(entries=True).replace(b'synthetic-test', marker.encode()))
    return data.getvalue()


def _stage(source_reference, marker='original'):
    return handover.stage_bank_archive(_payload(marker), PROFILE, connection=CONNECTION,
                                       accounts=[ACCOUNT], source_reference=source_reference)


def _financial_counts():
    return {doctype: frappe.db.count(doctype) for doctype in FINANCIAL}


def prepare():
    _guard()
    for doctype, name, values in (
        ('Company', COMPANY, {'company_name': COMPANY, 'abbr': 'BFH-CI', 'default_currency': 'CHF',
                              'country': 'Switzerland'}),
        ('Account', ACCOUNT, {'account_name': ACCOUNT, 'company': COMPANY, 'account_type': 'Bank',
                              'root_type': 'Asset', 'report_type': 'Balance Sheet', 'is_group': 0,
                              'disabled': 0, 'account_currency': 'CHF', 'iban': 'CH9300762011623852957'}),
        ('ebics Connection', CONNECTION, {'title': CONNECTION, 'company': COMPANY,
                                         'ebics_version': 'H005', 'scope': 'CH', 'enable_sync': 0}),
    ):
        if frappe.db.exists(doctype, name):
            raise RuntimeError('Acceptance requires a fresh test fixture')
        frappe.get_doc({'doctype': doctype, 'name': name, 'owner': 'Administrator', **values}).db_insert()
    counts = _financial_counts()
    frappe.db.commit()
    return counts


def commit_original(source_reference='initial', hold_lock=False):
    _guard()
    result = _stage(source_reference)
    if hold_lock:
        time.sleep(2)
    connection_id = frappe.db.sql('SELECT CONNECTION_ID()')[0][0]
    frappe.db.commit()
    return {'name': result['name'], 'connection_id': connection_id, 'replayed': result['replayed']}


def rollback_original():
    _guard()
    result = _stage('rolled-back', 'rolled-back')
    original = frappe.db.get_value(handover.DOCTYPE, result['name'], 'original_file')
    path = Path(frappe.get_doc('File', original).get_full_path())
    assert path.exists()
    frappe.db.rollback()
    assert not frappe.db.exists(handover.DOCTYPE, result['name'])
    assert not frappe.db.exists('File', original)
    assert not path.exists(), 'Outer rollback must remove the newly written binary'
    return {'outer_rollback': True}


def commit_after_caught_failure():
    _guard()
    frappe.db.set_value('ebics Connection', CONNECTION, 'title', 'Outer write survived')
    with patch.object(handover, '_original', side_effect=handover.BankFileError('Synthetic file-readback failure')):
        try:
            _stage('failed', 'failed')
        except handover.BankFileError:
            pass
        else:
            raise AssertionError('Injected failure was not observed')
    frappe.db.commit()
    return {'caught_failure_committed': True}


def verify(expected_receipts, financial_counts):
    _guard()
    names = frappe.get_all(handover.DOCTYPE, filters={'connection': CONNECTION}, pluck='name')
    assert len(names) == 1, names
    document = frappe.get_doc(handover.DOCTYPE, names[0])
    assert sorted(row.source_reference for row in document.receipts) == sorted(expected_receipts)
    assert handover._original(document) == _payload()
    assert handover.get_handover_preview(document.name)['read_only']
    assert frappe.db.count('File', {'attached_to_doctype': handover.DOCTYPE, 'attached_to_name': document.name}) == 1
    assert _financial_counts() == financial_counts, 'Financial rows changed during handover'
    return {'originals': 1, 'receipts': len(document.receipts), 'financial_rows_unchanged': True,
            'connection_title': frappe.db.get_value('ebics Connection', CONNECTION, 'title')}


def run_process_acceptance():
    """Run from bench's venv, but let each operation initialize its own Frappe process."""
    from concurrent.futures import ThreadPoolExecutor
    import subprocess
    from threading import Barrier

    if os.environ.get('CI') != 'true':
        raise RuntimeError('This acceptance runner is CI-only')
    module = 'erpnextswiss.erpnextswiss.tests.bank_handover_process_acceptance.'

    def execute(method, **kwargs):
        process = subprocess.run(['bench', '--site', 'test_site', 'execute', module + method,
                                  '--kwargs', json.dumps(kwargs)], capture_output=True, text=True, timeout=120)
        if process.returncode:
            raise RuntimeError(process.stdout + process.stderr)
        return json.loads(process.stdout.strip().splitlines()[-1])

    counts = execute('prepare')
    first = execute('commit_original')
    execute('verify', expected_receipts=['initial'], financial_counts=counts)
    repeated = execute('commit_original')
    assert first['name'] == repeated['name'] and repeated['replayed']
    assert first['connection_id'] != repeated['connection_id']
    execute('rollback_original')
    execute('commit_after_caught_failure')
    result = execute('verify', expected_receipts=['initial'], financial_counts=counts)
    assert result['connection_title'] == 'Outer write survived'
    barrier = Barrier(8)

    def receive(index):
        barrier.wait(timeout=30)
        return execute('commit_original', source_reference='shared' if index < 4 else 'worker-' + str(index),
                       hold_lock=True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        received = list(pool.map(receive, range(8)))
    assert len({row['connection_id'] for row in received}) == 8
    assert {row['name'] for row in received} == {first['name']}
    assert sum(row['replayed'] for row in received) == 3
    result = execute('verify', expected_receipts=['initial', 'shared', 'worker-4', 'worker-5', 'worker-6', 'worker-7'],
                     financial_counts=counts)
    print('PASS independent-process commit/readback, replay, outer rollback, caught failure and 8 receivers')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    run_process_acceptance()
