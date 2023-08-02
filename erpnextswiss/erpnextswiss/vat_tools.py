# -*- coding: utf-8 -*-
# Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

def check_vat_code(company, code, from_date, to_date, accounts, valuation="tax"):
    from frappe.utils import flt
    # get data from control
    vat_query = frappe.get_doc("VAT query", "viewVAT_{0}".format(code))
    control_items = frappe.db.sql("""SELECT * 
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
                query=vat_query.query,
                start_date=from_date, end_date=to_date).replace("{company}", company),
                as_dict=True)
    
    # get general ledger entries
    account_names = []
    for a in accounts:
        _accounts = frappe.db.sql("""
            SELECT `name` 
            FROM `tabAccount` 
            WHERE `account_number` = "{a}" OR `name` = "{a}";""".format(a=a), as_dict=True)
        for _a in _accounts:
            if _a['name'] not in account_names:
                account_names.append(_a['name'])
    
    gl_entries = frappe.db.sql("""
        SELECT `name`, `voucher_no`, SUM(`debit`) AS `debit`, SUM(`credit`) AS `credit` 
        FROM `tabGL Entry` 
        WHERE 
            `account` IN ("{accounts}")
            AND `posting_date` BETWEEN "{start}" AND "{end}"
            AND `company` = "{company}"
        GROUP BY `voucher_no`
            ;""".format(accounts="\", \"".join(account_names), start=from_date, end=to_date, company=company), 
        as_dict=True)
        
    # check that all control items are in the general ledger
    control_sum = 0
    for control_item in control_items:
        checked = False
        mismatch = False
        if valuation == "tax" and flt(control_item['total_taxes_and_charges']) != 0:
            control_sum += flt(control_item['total_taxes_and_charges'])
            # test by tax amount
            for entry in gl_entries:
                if entry['voucher_no'] == control_item['name']:
                    if abs(entry['debit'] - entry['credit']) == abs(control_item['total_taxes_and_charges']):
                        checked = True
                        continue
                    else:
                        mismatch = True
                        print("{0}: amount mismatch between {1} and {2}".format(entry['voucher_no'], 
                            abs(entry['debit'] - entry['credit']), abs(control_item['total_taxes_and_charges'])))
            if not checked and not mismatch:
                print("{0} not in general ledger (tax {1})".format(control_item['name'], flt(control_item['total_taxes_and_charges'])))
            #else:
            #    print("{0} OK".format(control_item['name']))
        elif valuation == "value" and flt(control_item['base_grand_total']) != 0:
            control_sum += flt(control_item['base_grand_total'])
            # test by valuation amount
            for entry in gl_entries:
                if entry['voucher_no'] == control_item['name']:
                    if abs(entry['debit'] - entry['credit']) == abs(control_item['base_grand_total']):
                        checked = True
                        continue
                    else:
                        mismatch = True
                        print("{0}: amount mismatch between {1} and {2}".format(entry['voucher_no'], 
                            abs(entry['debit'] - entry['credit']), abs(control_item['base_grand_total'])))
            if not checked and not mismatch:
                print("{0} not in general ledger ({1})".format(control_item['name'], flt(control_item['base_grand_total'])))
            #else:
            #    print("{0} OK".format(control_item['name']))
        else:
            print("Skipping {0}".format(control_item['name']))

    # check that all general ledger entries are in the control
    gl_sum = 0
    for entry in gl_entries:
        checked = False
        mismatch = False
        gl_sum += (entry['debit'] - entry['credit'])
        for control_item in control_items:
            if entry['voucher_no'] == control_item['name']:
                if valuation == "tax" and abs(entry['debit'] - entry['credit']) == abs(control_item['total_taxes_and_charges']):
                    checked = True
                    continue
                elif valuation == "value" and abs(entry['debit'] - entry['credit']) == abs(control_item['base_grand_total']):
                    checked = True
                    continue
                else:
                    mismatch = True
                    print("{0}: amount mismatch between {1} and {2}".format(entry['voucher_no'], 
                        abs(entry['debit'] - entry['credit']),
                        abs(control_item['total_taxes_and_charges']) if valuation == "tax" else abs(control_item['base_grand_total'])))
        if not checked and not mismatch:
            print("{0} not in control ({1})".format(entry['voucher_no'], abs(entry['debit'] - entry['credit'])))

    print("Control sum: {0}\tGL sum: {1}\t{2}\t{3}".format(round(control_sum, 2), round(gl_sum, 2),
        "OK" if (control_sum - gl_sum) < 0.01 else "Check",
        (round(control_sum, 2) - round(abs(gl_sum), 2))))
    
