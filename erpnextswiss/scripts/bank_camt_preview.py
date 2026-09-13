"""Validated camt envelopes handed to the existing matcher, never to a writer.

No public endpoint: callers supply the company's configured accounts, not an
IBAN lookup across the ERP. Originals and every entry survive the preview.
"""

from decimal import Decimal

from lxml import etree

from erpnextswiss.scripts.bank_file_admission import BankFileError, PROFILES, _parser, read_bank_archive


MAX_STATEMENTS = 256
MAX_ENTRIES = 10000


def _text(node, path):
    return node.findtext(path)


def _date(node, path):
    return _text(node, path + '/Dt') or _text(node, path + '/DtTm')


def _money(node):
    amount = node.find('Amt')
    return {'amount': amount.text, 'currency': amount.get('Ccy'),
            'credit_debit': _text(node, 'CdtDbtInd')}


def _signed(money):
    return Decimal(money['amount']) * (-1 if money['credit_debit'] == 'DBIT' else 1)


def _local_tree(node, namespace):
    # Only the validated standard vocabulary enters the old descendant-based
    # matcher. Supplementary payloads must never impersonate bank fields.
    if not isinstance(node.tag, str) or not node.tag.startswith(namespace):
        return None
    name = node.tag[len(namespace):]
    if name == 'SplmtryData':
        return None
    local = etree.Element(name, {key: value for key, value in node.attrib.items() if not key.startswith('{')})
    local.text = node.text
    for child in node:
        converted = _local_tree(child, namespace)
        if converted is not None:
            local.append(converted)
    return local


def prepare_camt_archive(payload, profile):
    """Format-only preparation. It grants no account access or import approval."""
    archive = read_bank_archive(payload, profile)
    namespace = '{urn:iso:std:iso:20022:tech:xsd:' + profile + '}'
    unit = 'Stmt' if profile == 'camt.053.001.08' else 'Ntfctn'
    statements = []
    entry_count = 0
    for file_index, source in enumerate(archive.files):
        document = _local_tree(etree.fromstring(source.content, _parser()), namespace)
        body = document.find(PROFILES[profile])
        for statement_index, node in enumerate(body.findall(unit)):
            entries = []
            for entry_index, entry in enumerate(node.findall('Ntry')):
                entry_count += 1
                if entry_count > MAX_ENTRIES:
                    raise BankFileError('Bank preview exceeds entry limits')
                entries.append({'index': entry_index, **_money(entry),
                                'status': _text(entry, 'Sts/Cd') or _text(entry, 'Sts/Prtry'),
                                'booking_date': _date(entry, 'BookgDt'), 'value_date': _date(entry, 'ValDt'),
                                'reversal': _text(entry, 'RvslInd') in ('true', '1'),
                                'reference': _text(entry, 'AcctSvcrRef'), 'entry_reference': _text(entry, 'NtryRef'),
                                'detail_count': len(entry.findall('NtryDtls/TxDtls')),
                                'xml': etree.tostring(entry, encoding='unicode')})
            balances = [{**_money(balance), 'type': _text(balance, 'Tp/CdOrPrtry/Cd'),
                         'proprietary_type': _text(balance, 'Tp/CdOrPrtry/Prtry'), 'date': _date(balance, 'Dt')}
                        for balance in node.findall('Bal')]
            statements.append({'file_index': file_index, 'file_sha256': source.sha256,
                               'statement_index': statement_index, 'statement_id': _text(node, 'Id'),
                               'message_id': _text(body, 'GrpHdr/MsgId'),
                               'message_page': _text(body, 'GrpHdr/MsgPgntn/PgNb'),
                               'message_last_page': _text(body, 'GrpHdr/MsgPgntn/LastPgInd'),
                               'page': _text(node, 'StmtPgntn/PgNb') or _text(node, 'NtfctnPgntn/PgNb'),
                               'last_page': _text(node, 'StmtPgntn/LastPgInd') or _text(node, 'NtfctnPgntn/LastPgInd'),
                               'sequence': _text(node, 'ElctrncSeqNb'),
                               'created_at': _text(node, 'CreDtTm') or _text(body, 'GrpHdr/CreDtTm'),
                               'from_date': _text(node, 'FrToDt/FrDtTm'), 'to_date': _text(node, 'FrToDt/ToDtTm'),
                               'copy_indicator': _text(node, 'CpyDplctInd'),
                               'iban': _text(node, 'Acct/Id/IBAN'), 'currency': _text(node, 'Acct/Ccy'),
                               'balances': balances, 'entries': entries})
            if len(statements) > MAX_STATEMENTS or entry_count > MAX_ENTRIES:
                raise BankFileError('Bank preview exceeds statement or entry limits')
    return archive, statements


def _entry_issues(entry, settings):
    issues = []
    if entry['status'] != 'BOOK':
        issues.append('not_booked')
    if not entry['booking_date']:
        issues.append('missing_booking_date')
    if entry['reversal']:
        issues.append('reversal_requires_review')
    node = etree.fromstring(entry['xml'].encode(), _parser())
    details = node.findall('NtryDtls/TxDtls')
    always_entry = bool(int(settings.get('always_use_entry_amount') or 0))
    always_direction = bool(int(settings.get('always_use_entry_transaction_type') or 0))
    if always_entry and len(details) > 1:
        issues.append('aggregate_setting_would_repeat_amount')
    amounts = []
    for detail in details:
        amount = detail.find('Amt')
        if amount is None:
            amount = detail.find('AmtDtls/TxAmt/Amt')
        direction = _text(detail, 'CdtDbtInd') or entry['credit_debit']
        if always_direction and direction != entry['credit_debit']:
            issues.append('aggregate_setting_would_change_direction')
        if always_entry and len(details) == 1:
            pass  # The existing explicit setting uses the single booking amount.
        elif amount is None and len(details) > 1:
            issues.append('missing_batch_detail_amount')
        elif amount is not None:
            if amount.get('Ccy') != entry['currency']:
                issues.append('detail_currency_differs_from_booking')
            amounts.append(Decimal(amount.text) * (-1 if direction == 'DBIT' else 1))
        if detail.find('RtrInf') is not None:
            issues.append('return_requires_review')
    if amounts and len(amounts) == len(details) and sum(amounts) != _signed(entry):
        issues.append('detail_sum_differs_from_booking')
    return list(dict.fromkeys(issues))


def _matcher_xml(text):
    node = etree.fromstring(text.encode(), _parser())
    for element in node.iter():
        element.tag = element.tag.lower()
        attributes = {name.lower(): value for name, value in element.attrib.items()}
        element.attrib.clear()
        element.attrib.update(attributes)
    return etree.tostring(node, encoding='unicode')


def _balance_check(statement):
    if statement['page'] or statement['message_page']:
        return 'requires_page_assembly'
    opening = [b for b in statement['balances'] if b['type'] == 'OPBD']
    closing = [b for b in statement['balances'] if b['type'] == 'CLBD']
    if len(opening) != 1 or len(closing) != 1:
        return 'not_available'
    movement = sum(_signed(e) for e in statement['entries'] if e['status'] == 'BOOK')
    return 'matched' if _signed(opening[0]) + movement == _signed(closing[0]) else 'mismatch'


def preview_camt_archive(payload, profile, *, company, accounts):
    """Read-only handover using configured accounts and native current permissions.

    Results are preview/evidence, never ready-to-book instructions. File/ordinal
    identity preserves provenance; it is NOT cross-message business deduplication.
    """
    import frappe
    from erpnextswiss.scripts.bank_matching_scope import BankMatchingScope
    from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt_transactions

    frappe.only_for(('Accounts User', 'Accounts Manager', 'System Manager'))
    if (not isinstance(company, str) or not company.strip() or not isinstance(accounts, (list, tuple))
            or not 0 < len(accounts) <= 64 or any(not isinstance(a, str) or not a.strip() for a in accounts)):
        raise BankFileError('Explicit company and configured bank accounts are required')
    scopes = {}
    for account in accounts:
        scope = BankMatchingScope(account)
        key = (scope.iban, scope.currency)
        if scope.company != company or not scope.iban or not scope.currency or key in scopes:
            raise BankFileError('Configured bank account binding is missing or ambiguous')
        scopes[key] = scope
    archive, statements = prepare_camt_archive(payload, profile)
    # Validate EVERY statement before the first financial candidate query. A bad
    # later account/file cannot yield a partially authorized match result.
    for statement in statements:
        matches = [scope for (iban, currency), scope in scopes.items() if iban == statement['iban']
                   and (not statement['currency'] or statement['currency'] == currency)]
        if len(matches) != 1:
            raise BankFileError('Bank file account binding is absent or ambiguous')
        scope = matches[0]
        if any(row['currency'] != scope.currency for row in statement['balances'] + statement['entries']):
            raise BankFileError('Bank amounts differ from the configured account currency')
        statement.update(account=scope.account, company=scope.company, currency=scope.currency)
    settings = frappe.get_doc('ERPNextSwiss Settings', 'ERPNextSwiss Settings')
    for statement in statements:
        eligible = []
        statement['balance_check'] = _balance_check(statement)
        for entry in statement['entries']:
            entry.update(issues=_entry_issues(entry, settings), candidates=[])
            if statement['balance_check'] == 'mismatch':
                entry['issues'].append('statement_balance_mismatch')
            entry['matching_state'] = 'review_required' if entry['issues'] else 'previewed'
            if not entry['issues']:
                eligible.append(entry)
        if eligible:
            candidates = read_camt_transactions([_matcher_xml(e['xml']) for e in eligible], statement['account'],
                                                settings, read_only=True, xml_entries=True)
            for candidate in candidates:
                eligible[candidate.pop('_camt_entry_index')]['candidates'].append(candidate)
            for entry in eligible:
                entry['suppressed_by_existing_matcher'] = max(1, entry['detail_count']) - len(entry['candidates'])
    return {'archive': archive, 'statements': statements, 'read_only': True}
