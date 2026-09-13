"""Pure envelope/adapter tests against the packaged XSD; no Frappe imports."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import unittest
from unittest.mock import patch

from lxml import etree

from erpnextswiss.erpnextswiss.tests.test_bank_file_admission import PROFILE, xml, zipped
from erpnextswiss.scripts import bank_camt_preview as preview
from erpnextswiss.scripts.bank_file_admission import BankFileError, PROFILES


def detailed_xml(profile=PROFILE, currency='CHF', amounts=('12.34',), reference='synthetic-reference',
                 remark='Synthetic & <reference> / customer', foreign_amount=False):
    root = etree.fromstring(xml(profile, currency, entries=True))
    ns = {'b': root.nsmap[None]}
    tag = lambda name: '{' + ns['b'] + '}' + name
    entry = root.find('.//b:Ntry', ns)
    entry.find('b:Amt', ns).text = str(sum(Decimal(a) for a in amounts))
    details = etree.SubElement(entry, tag('NtryDtls'))
    for index, amount in enumerate(amounts):
        tx = etree.SubElement(details, tag('TxDtls'))
        refs = etree.SubElement(tx, tag('Refs'))
        etree.SubElement(refs, tag('AcctSvcrRef')).text = reference + '-' + str(index)
        etree.SubElement(tx, tag('Amt'), Ccy=currency).text = amount
        if foreign_amount:
            amt_details = etree.SubElement(tx, tag('AmtDtls'))
            tx_amount = etree.SubElement(amt_details, tag('TxAmt'))
            etree.SubElement(tx_amount, tag('Amt'), Ccy='USD').text = '999.12'
        parties = etree.SubElement(tx, tag('RltdPties'))
        debtor = etree.SubElement(parties, tag('Dbtr'))
        party = etree.SubElement(debtor, tag('Pty'))
        etree.SubElement(party, tag('Nm')).text = 'Test & Co <Bank> / Customer'
        remit = etree.SubElement(tx, tag('RmtInf'))
        etree.SubElement(remit, tag('Ustrd')).text = remark
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8')


def entry_from(content):
    return preview.prepare_camt_archive(zipped([('test.xml', content)]), PROFILE)[1][0]['entries'][0]


class TestBankCamtPreview(unittest.TestCase):
    def test_both_profiles_keep_each_file_statement_and_original(self):
        for profile in PROFILES:
            content = xml(profile, multiple=True, entries=True)
            payload = zipped([('first.xml', content), ('second.xml', content)])
            archive, statements = preview.prepare_camt_archive(payload, profile)
            self.assertEqual(archive.sha256, sha256(payload).hexdigest())
            self.assertEqual(archive.files[0].content, content)
            self.assertEqual([(s['file_index'], s['statement_index']) for s in statements], [(0, 0), (0, 1), (1, 0), (1, 1)])
            self.assertTrue(all(len(s['entries']) == 1 for s in statements))
            self.assertEqual(statements[0]['message_id'], 'synthetic-test')

    def test_prefixed_utf16_roundtrip_does_not_treat_bank_text_as_html(self):
        for profile in PROFILES:
            root = etree.fromstring(detailed_xml(profile))
            prefixed = etree.Element(root.tag, nsmap={'bank': root.nsmap[None]})
            prefixed.extend(root)
            content = etree.tostring(prefixed, encoding='UTF-16', xml_declaration=True)
            archive, statements = preview.prepare_camt_archive(zipped([('test.xml', content)]), profile)
            self.assertEqual(archive.files[0].content, content)
            entry = statements[0]['entries'][0]
            converted = etree.fromstring(preview._matcher_xml(entry['xml']).encode())
            self.assertEqual(converted.findtext('ntrydtls/txdtls/rmtinf/ustrd'), 'Synthetic & <reference> / customer')
            self.assertEqual(converted.findtext('ntrydtls/txdtls/rltdpties/dbtr/pty/nm'), 'Test & Co <Bank> / Customer')

    def test_supplementary_fields_cannot_impersonate_standard_transactions(self):
        root = etree.fromstring(detailed_xml())
        ns = root.nsmap[None]
        tx = root.find('.//{' + ns + '}TxDtls')
        extra = etree.SubElement(tx, '{' + ns + '}SplmtryData')
        envelope = etree.SubElement(extra, '{' + ns + '}Envlp')
        alien = etree.SubElement(envelope, '{urn:example:extra}Payload')
        etree.SubElement(alien, '{' + ns + '}TxDtls')
        etree.SubElement(alien, '{' + ns + '}Amt', Ccy='CHF').text = '1000000'
        content = etree.tostring(root)
        archive, statements = preview.prepare_camt_archive(zipped([('test.xml', content)]), PROFILE)
        self.assertIn(b'1000000', archive.files[0].content)
        self.assertEqual(statements[0]['entries'][0]['detail_count'], 1)
        self.assertNotIn('1000000', statements[0]['entries'][0]['xml'])

    def test_zero_entry_negative_balance_and_decimal_precision_survive(self):
        content = xml().replace(b'1234.00', b'1234.12345').replace(b'CRDT', b'DBIT')
        _, statements = preview.prepare_camt_archive(zipped([('test.xml', content)]), PROFILE)
        statement = statements[0]
        self.assertEqual(statement['entries'], [])
        self.assertEqual(statement['balances'][0]['amount'], '1234.12345')
        self.assertEqual(preview._signed(statement['balances'][0]), Decimal('-1234.12345'))
        self.assertEqual(preview._balance_check(statement), 'not_available')

    def test_incomplete_or_mismatched_input_is_not_partially_prepared(self):
        for profile in PROFILES:
            with self.assertRaises(BankFileError):
                preview.prepare_camt_archive(zipped([('one.xml', xml(profile)), ('two.xml', b'<broken>')]), profile)
        with patch.object(preview, 'MAX_ENTRIES', 1), self.assertRaises(BankFileError):
            preview.prepare_camt_archive(zipped([('test.xml', xml(entries=True, multiple=True))]), PROFILE)
        with patch.object(preview, 'MAX_STATEMENTS', 1), self.assertRaises(BankFileError):
            preview.prepare_camt_archive(zipped([('test.xml', xml(multiple=True))]), PROFILE)

    def test_normal_details_sum_exactly_and_prefer_direct_amount_to_foreign_txamt(self):
        for amounts in [('0.10', '0.20'), ('12.34',), ('0.12345', '0.00001')]:
            entry = entry_from(detailed_xml(amounts=amounts, foreign_amount=True))
            self.assertEqual(preview._entry_issues(entry, {}), [])

    def test_batch_inconsistency_and_incomplete_amounts_require_review(self):
        base = entry_from(detailed_xml(amounts=('10', '20')))
        self.assertIn('aggregate_setting_would_repeat_amount', preview._entry_issues(base, {'always_use_entry_amount': True}))
        changed = {**base, 'amount': '31'}
        self.assertIn('detail_sum_differs_from_booking', preview._entry_issues(changed, {}))
        node = etree.fromstring(base['xml'].encode())
        detail = node.find('NtryDtls/TxDtls')
        detail.remove(detail.find('Amt'))
        changed = {**base, 'xml': etree.tostring(node, encoding='unicode')}
        self.assertIn('missing_batch_detail_amount', preview._entry_issues(changed, {}))

    def test_pending_reversal_missing_date_and_foreign_detail_never_get_guessed(self):
        entry = entry_from(detailed_xml())
        for values, expected in [({'status': 'PDNG'}, 'not_booked'), ({'reversal': True}, 'reversal_requires_review'),
                                 ({'booking_date': None}, 'missing_booking_date')]:
            self.assertIn(expected, preview._entry_issues({**entry, **values}, {}))
        node = etree.fromstring(entry['xml'].encode())
        node.find('NtryDtls/TxDtls/Amt').set('Ccy', 'USD')
        changed = {**entry, 'xml': etree.tostring(node, encoding='unicode')}
        self.assertIn('detail_currency_differs_from_booking', preview._entry_issues(changed, {}))

    def test_balance_arithmetic_uses_direction_and_does_not_claim_complete_pages(self):
        _, statements = preview.prepare_camt_archive(zipped([('test.xml', xml(entries=True))]), PROFILE)
        statement = deepcopy(statements[0])
        statement['balances'] = [{'type': 'OPBD', 'amount': '10', 'credit_debit': 'DBIT'},
                                 {'type': 'CLBD', 'amount': '2.34', 'credit_debit': 'CRDT'}]
        self.assertEqual(preview._balance_check(statement), 'matched')
        statement['balances'][1]['amount'] = '2.35'
        self.assertEqual(preview._balance_check(statement), 'mismatch')
        statement['page'] = '1'
        self.assertEqual(preview._balance_check(statement), 'requires_page_assembly')
