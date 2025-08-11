# -*- coding: utf-8 -*-
# Copyright (c) 2017-2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import html          # used to escape xml content
import ast
from frappe.utils import cint
from frappe.utils.data import rounded
from erpnextswiss.erpnextswiss.finance import get_booking_pairs
from frappe import _
from bs4 import BeautifulSoup

class AbacusExportFile(Document):
    def submit(self):
        if cint(self.aggregated):
            # aggregated method: do not pick and mark records (based on general ledger)
            self.get_account_balances()
        else:
            # transaction-based 
            self.get_transactions()
        return
    
    def on_cancel(self):
        sinvs = self.get_references("Sales Invoice")
        pinvs = self.get_references("Purchase Invoice")
        pes = self.get_references("Payment Entry")
        jvs = self.get_references("Journal Entry")
        set_export_flag("Sales Invoice", self.get_sql_list(sinvs), 0)
        set_export_flag("Purchase Invoice", self.get_sql_list(pinvs), 0)
        set_export_flag("Payment Entry", self.get_sql_list(pes), 0)
        set_export_flag("Journal Entry", self.get_sql_list(jvs), 0)
        return
        
    # find all transactions, add the to references and mark as collected
    def get_transactions(self):
        # check elimination of zero-sum transactions
        if cint(self.exclude_zero_sum_txs) == 1:
            sinv_filter = """AND `tabSales Invoice`.`grand_total` != 0"""
            pinv_filter = """AND `tabPurchase Invoice`.`grand_total` != 0"""
        else:
            sinv_filter = ""
            pinv_filter = ""
             
        # get all documents
        if cint(self.debtors_only):
            document_query = """SELECT 
                    "Sales Invoice" AS `dt`,
                    `tabSales Invoice`.`name` AS `dn`
                FROM `tabSales Invoice`
                WHERE
                    `tabSales Invoice`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                    AND `tabSales Invoice`.`docstatus` = 1
                    AND `tabSales Invoice`.`exported_to_abacus` = 0
                    AND `tabSales Invoice`.`company` = '{company}'
                    {sinv_filter}
                UNION SELECT 
                    "Payment Entry" AS `dt`,
                    `tabPayment Entry`.`name` AS `dn`
                FROM `tabPayment Entry`
                WHERE
                    `tabPayment Entry`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                    AND `tabPayment Entry`.`docstatus` = 1
                    AND `tabPayment Entry`.`exported_to_abacus` = 0
                    AND `tabPayment Entry`.`company` = '{company}'
                    AND `tabPayment Entry`.`payment_type` = 'Receive'
                UNION SELECT 
                    "Journal Entry" AS `dt`,
                    `tabJournal Entry`.`name` AS `dn`
                FROM `tabJournal Entry`
                WHERE
                    `tabJournal Entry`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                    AND `tabJournal Entry`.`docstatus` = 1
                    AND `tabJournal Entry`.`exported_to_abacus` = 0
                    AND (SELECT COUNT(`name`) 
                         FROM `tabJournal Entry Account` 
                         WHERE `tabJournal Entry Account`.`parent` = `tabJournal Entry`.`name`
                           AND `tabJournal Entry Account`.`party_type` = 'Customer') > 0
                    AND `tabJournal Entry`.`company` = '{company}';""".format(
                    start_date=self.from_date, end_date=self.to_date, 
                    company=self.company, sinv_filter=sinv_filter)
        else:
            document_query = """SELECT 
                        "Sales Invoice" AS `dt`,
                        `tabSales Invoice`.`name` AS `dn`
                    FROM `tabSales Invoice`
                    WHERE
                        `tabSales Invoice`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                        AND `tabSales Invoice`.`docstatus` = 1
                        AND `tabSales Invoice`.`exported_to_abacus` = 0
                        AND `tabSales Invoice`.`company` = '{company}'
                        {sinv_filter}
                    UNION SELECT 
                        "Purchase Invoice" AS `dt`,
                        `tabPurchase Invoice`.`name` AS `dn`
                    FROM `tabPurchase Invoice`
                    WHERE
                        `tabPurchase Invoice`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                        AND `tabPurchase Invoice`.`docstatus` = 1
                        AND `tabPurchase Invoice`.`exported_to_abacus` = 0
                        AND `tabPurchase Invoice`.`company` = '{company}'
                        {pinv_filter}
                    UNION SELECT 
                        "Payment Entry" AS `dt`,
                        `tabPayment Entry`.`name` AS `dn`
                    FROM `tabPayment Entry`
                    WHERE
                        `tabPayment Entry`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                        AND `tabPayment Entry`.`docstatus` = 1
                        AND `tabPayment Entry`.`exported_to_abacus` = 0
                        AND `tabPayment Entry`.`company` = '{company}'
                    UNION SELECT 
                        "Journal Entry" AS `dt`,
                        `tabJournal Entry`.`name` AS `dn`
                    FROM `tabJournal Entry`
                    WHERE
                        `tabJournal Entry`.`posting_date` BETWEEN '{start_date}' AND '{end_date}'
                        AND `tabJournal Entry`.`docstatus` = 1
                        AND `tabJournal Entry`.`exported_to_abacus` = 0
                        AND `tabJournal Entry`.`company` = '{company}';""".format(
                        start_date=self.from_date, end_date=self.to_date, 
                        company=self.company, sinv_filter=sinv_filter, pinv_filter=pinv_filter)
        
        docs = frappe.db.sql(document_query, as_dict=True)
        
        # clear all children
        self.references = []
        
        # add to child table
        for doc in docs:
            row = self.append('references', {'dt': doc['dt'], 'dn': doc['dn']})
        self.save()
        
        # mark as exported
        sinvs = self.get_docs(docs, "Sales Invoice")
        pinvs = self.get_docs(docs, "Purchase Invoice")
        pes = self.get_docs(docs, "Payment Entry")
        jvs = self.get_docs(docs, "Journal Entry")
        set_export_flag("Sales Invoice", self.get_sql_list(sinvs), 1)
        set_export_flag("Purchase Invoice", self.get_sql_list(pinvs), 1)
        set_export_flag("Payment Entry", self.get_sql_list(pes), 1)
        set_export_flag("Journal Entry", self.get_sql_list(jvs), 1)
        return
    
    # extract document names of one doctype as list
    def get_docs(self, references, dt):
        docs = []
        for d in references:
            if d['dt'] == dt:
                docs.append(d['dn'])
        return docs
    
    def get_references(self, dt):
        docs = []
        for d in self.references:
            if d.get('dt') == dt:
                docs.append(d.get('dn'))
        return docs
        
    # safe call to get SQL IN statement    
    def get_sql_list(self, docs):
        if docs:
            return (','.join('"{0}"'.format(w) for w in docs))
        else:
            return '""'
    
    # reset export flags
    def reset_export_flags(self):
        sql_query = """UPDATE `tabGL Entry` SET `exported_to_abacus` = 0;"""
        frappe.db.sql(sql_query, as_dict=True)
        sql_query = """UPDATE `tabSales Invoice` SET `exported_to_abacus` = 0;"""
        frappe.db.sql(sql_query, as_dict=True)
        sql_query = """UPDATE `tabPayment Entry` SET `exported_to_abacus` = 0;"""
        frappe.db.sql(sql_query, as_dict=True)
        sql_query = """UPDATE `tabPurchase Invoice` SET `exported_to_abacus` = 0;"""
        frappe.db.sql(sql_query, as_dict=True)
        sql_query = """UPDATE `tabJournal Entry` SET `exported_to_abacus` = 0;"""
        frappe.db.sql(sql_query, as_dict=True)
        return { 'message': 'OK' }
    
    # get account number
    def get_account_number(self, account_name):
        if account_name:
            return frappe.get_value("Account", account_name, "account_number")
        else:
            return None
    
    # aggregation by accounts
    def get_account_balances(self):
        # for each account, compute period balance (see trial balance)
        sql_query = """
            SELECT
                `tabGL Entry`.`account`,
                `tabAccount`.`account_number`, 
                SUM(`tabGL Entry`.`debit`) AS `total_debit`,
                SUM(`tabGL Entry`.`credit`) AS `total_credit`
            FROM `tabGL Entry`
            LEFT JOIN `tabAccount` ON `tabAccount`.`name` = `tabGL Entry`.`account`
            WHERE
                `tabAccount`.`company` = "{company}"
                AND `tabGL Entry`.`posting_date` BETWEEN "{from_date}" AND "{to_date}"
            GROUP BY `tabGL Entry`.`account`
            ORDER BY `tabAccount`.`name` ASC;
        """.format(company=self.company, from_date=self.from_date, to_date=self.to_date)
        
        balances = frappe.db.sql(sql_query, as_dict=True)
        for balance in balances:
            self.append("balances", {
                'account': balance.get("account"),
                'account_number': balance.get("account_number"),
                'debit': balance.get("total_debit"),
                'credit': balance.get("total_credit"),
                'balance': balance.get("total_debit") - balance.get("total_credit")
            })
        
        # apply
        self.save()
        
        return
        
    # prepare transfer file
    def render_transfer_file(self, restrict_currencies=None):
        if restrict_currencies and type(restrict_currencies) == str:
            restrict_currencies = ast.list_eval(restrict_currencies)
        # collect task information
        if self.aggregated == 1:
            """ aggregated method """
            data = {
                'transactions': self.get_aggregated_transactions()
            }
                
        else:
            # normal method (each document)
            data = {
                'transactions': self.get_individual_transactions(restrict_currencies)
            }            
            
        
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/abacus_export_file/transfer_file.html', data)
        return {'content': content}

    # get aggregated transactions 
    def get_aggregated_transactions(self):
        transactions = []
        
        # first account is the collective account, following will be against accounts; prevent index issue on empty periods
        if len(self.balances) < 2:
            return transactions
        
        """ Method: export as opening balance with a balance per account
        # compile split-account records
        against_singles = []
        for balance in self.balances[1:]:
            against_singles.append({
                'account': balance.get('account_number'),
                'amount': rounded(balance.get('balance'), 2),
                'currency': self.currency
            })
        
        # create transaction data
        transactions.append({
            'account': self.balances[0].get('account_number'), 
            'amount': rounded(self.balances[0].get('balance'), 2), 
            'against_singles': against_singles,
            'debit_credit': "D", 
            'date': self.to_date, 
            'currency': self.currency, 
            'tax_account': None, 
            'tax_amount': None, 
            'tax_rate': 0, 
            'tax_code': None, 
            'tax_currency': self.currency,
            'text1': "Aggregated {0}".format(self.name),
            'exchange_rate': 1
        })
        """
        
        """ Method: generate booking pairs """
        vouchers = frappe.db.sql("""
            SELECT `voucher_type`, `voucher_no`
            FROM `tabGL Entry`
            WHERE 
                `tabGL Entry`.`company` = "{company}"
                AND `tabGL Entry`.`posting_date` BETWEEN "{from_date}" AND "{to_date}"
            GROUP BY `tabGL Entry`.`voucher_no`;
            """.format(company=self.company, from_date=self.from_date, to_date=self.to_date), as_dict=True)
        
        # structure: key is "account|account", values is a dict with {'amount', 'exchange_rate', 'foreign_amount?}
        aggregates_booking_pairs = {}
        
        f = open("/tmp/booking_pairs.csv", "w")
        f.write("{0};{1};{2};{3};{4}\n".format(
                    "debit_account", 
                    "credit_account", 
                    "amount", 
                    "foreign_amount",
                    "voucher_no"))
        for voucher in vouchers:
            new_booking_pairs = get_booking_pairs(voucher['voucher_type'], voucher['voucher_no'])
            
            for k, v in new_booking_pairs.items():
                if k not in aggregates_booking_pairs:
                    aggregates_booking_pairs[k] = v
                else:
                    aggregates_booking_pairs[k]['amount'] += v['amount']
                    aggregates_booking_pairs[k]['foreign_amount'] += v['foreign_amount']
        
                # for debug only
                f.write("{0};{1};{2};{3};{4}\n".format(
                    v.get("debit_account"), 
                    v.get("credit_account"), 
                    v.get("amount"), 
                    v.get("foreign_amount"),
                    voucher.get("voucher_no")))
                
        f.close()
        
        # create transaction data
        for k, v in aggregates_booking_pairs.items():
            # determine if one account is a tax account
            debit_account_doc = frappe.get_doc("Account", v.get('debit_account'))
            credit_account_doc = frappe.get_doc("Account", v.get('credit_account'))
            if debit_account_doc.account_type == "Tax" or credit_account_doc.account_type == "Tax":
                # skip tax accunt records (will be integrated
                continue
                
            # determine tax rate
            tax_rate = debit_account_doc.tax_rate or credit_account_doc.tax_rate or 0
            tax_account = None
            tax_code = None
            if tax_rate:
                tax_accounts = frappe.get_all("Account", 
                    filters={
                        'company': self.company,
                        'account_type': 'Tax',
                        'tax_rate': tax_rate
                    },
                    fields=['name']
                )
                if len(tax_accounts) > 0:
                    tax_account = tax_accounts[0]['name']
                tax_templates = frappe.db.sql("""
                    SELECT `tabSales Taxes and Charges Template`.`tax_code`
                    FROM `tabSales Taxes and Charges`
                    LEFT JOIN `tabSales Taxes and Charges Template` ON `tabSales Taxes and Charges`.`parent` = `tabSales Taxes and Charges Template`.`name`
                    WHERE
                        `tabSales Taxes and Charges`.`parenttype` = "Sales Taxes and Charges Template"
                        AND `tabSales Taxes and Charges`.`rate` = {tax_rate};
                    """.format(tax_rate=tax_rate), as_dict=True)
                if len(tax_templates) > 0:
                    tax_code = tax_templates[0]['tax_code']
                    
            net_amount = rounded(v.get('amount'), 2)
            tax_amount = rounded((net_amount * (tax_rate / 100)), 2)
            gross_amount = rounded((net_amount + tax_amount), 2)
            
            foreign_gross_amount = rounded((gross_amount * v.get('exchange_rate')), 2)
            foreign_net_amount = rounded((v.get('amount') * v.get('exchange_rate')), 2)
            foreign_tax_amount = foreign_gross_amount - foreign_net_amount
            
            # determine foreign currency
            foreign_currency = debit_account_doc.account_currency \
                if debit_account_doc.account_currency != self.currency \
                else credit_account_doc.account_currency
                
            transactions.append({
                'account': self.get_account_number(v.get('debit_account')), 
                'amount': foreign_gross_amount, 
                'key_amount': gross_amount,
                'exchange_rate': v.get('exchange_rate'),
                'against_singles': [{
                    'account': self.get_account_number(v.get('credit_account')),
                    'amount': foreign_net_amount,
                    'key_amount': net_amount,
                    'currency': self.currency
                }],
                'debit_credit': "D", 
                'date': self.to_date, 
                'currency': foreign_currency, 
                'key_currency': self.currency,
                'tax_account': self.get_account_number(tax_account), 
                'tax_amount': tax_amount, 
                'tax_rate': tax_rate, 
                'tax_code': tax_code, 
                'tax_currency': self.currency,
                'text1': "Aggregated {0} ({1}. {2})".format(k, tax_rate, tax_amount)
            })
        
        # note account1|account2 and account2|account1 are recorded separately
        
        return transactions


    def get_individual_transactions(self, restrict_currencies=None):
        base_currency = frappe.get_value("Company", self.company, "default_currency")
        transactions = []
        sinvs = self.get_docs([ref.__dict__ for ref in self.references], "Sales Invoice")
        sql_query = """SELECT `tabSales Invoice`.`name`, 
                  `tabSales Invoice`.`posting_date`, 
                  `tabSales Invoice`.`currency`, 
                  `tabSales Invoice`.`grand_total` AS `debit`, 
                  `tabSales Invoice`.`base_grand_total` AS `base_debit`,
                  `tabSales Invoice`.`debit_to`,
                  `tabSales Invoice`.`net_total` AS `income`, 
                  `tabSales Invoice`.`base_net_total` AS `base_income`,  
                  `tabSales Invoice`.`base_total_taxes_and_charges` AS `tax`, 
                  `tabSales Taxes and Charges`.`account_head`,
                  `tabSales Invoice`.`taxes_and_charges`,
                  `tabSales Taxes and Charges`.`rate`,
                  `tabSales Invoice`.`customer_name`,
                  `tabSales Invoice`.`conversion_rate`
                FROM `tabSales Invoice`
                LEFT JOIN `tabSales Taxes and Charges` ON (`tabSales Invoice`.`name` = `tabSales Taxes and Charges`.`parent` AND  `tabSales Taxes and Charges`.`idx` = 1)
                WHERE `tabSales Invoice`.`name` IN ({sinvs});""".format(sinvs=self.get_sql_list(sinvs))
        sinv_items = frappe.db.sql(sql_query, as_dict=True)    
        for item in sinv_items:
            # if this is a zero-sum transaction, skip
            if item['debit'] == 0:
                continue
                
            if item.taxes_and_charges:
                tax_record = frappe.get_doc("Sales Taxes and Charges Template", item.taxes_and_charges)
                tax_code = tax_record.tax_code
            else:
                tax_code = None
            # create content
            if item.customer_name:
                text2 = html.escape(item.customer_name)
            else:
                text2 = ""
            # find against accounts
            against_positions = []
            for account in frappe.db.sql("""
                SELECT 
                    `income_account`, 
                    SUM(`base_net_amount`) AS `key_amount`, 
                    SUM(`net_amount`) AS `amount`
                FROM `tabSales Invoice Item`
                WHERE `parent` = "{sinv}"
                GROUP BY `income_account`;""".format(sinv=item.name), as_dict=True):
                if account['amount']:               # only append non-zero entries
                    tax_amount = rounded((account['amount'] * (item.rate or 0) / 100), 2)
                    against_positions.append({
                        'account': self.get_account_number(account['income_account']),
                        'amount': rounded(account['amount'], 2),
                        'currency': item.currency,
                        'key_amount': rounded(account['key_amount'], 2),
                        'key_currency': base_currency,
                        'tax_amount': tax_amount,
                        'key_tax_amount': rounded((tax_amount * item.conversion_rate), 2)
                    })
            
            _tx = {
                'account': self.get_account_number(item.debit_to), 
                'amount': rounded(item.base_debit, 2), 
                'currency': base_currency, 
                'key_amount': rounded(item.base_debit, 2), 
                'key_currency': base_currency,
                'exchange_rate': item.conversion_rate,
                'against_singles': against_positions,
                'debit_credit': "D", 
                'date': item.posting_date, 
                'tax_account': self.get_account_number(item.account_head) or None, 
                # 'tax_amount': item.tax or None,    # this takes the complete tax amount
                # 'tax_amount': None,                  # calculate on the basis of the item
                'tax_amount': (item.base_debit * (item.rate or 0) / 100),
                'tax_rate': rounded(item.rate, 2) if item.rate else 0, 
                'tax_currency': base_currency,
                'tax_code': tax_code or "312", 
                'text1': html.escape(item.name),
                'text2': text2
            }
            
            if not restrict_currencies or item.currency in restrict_currencies:
                _tx['amount'] = rounded(item.debit, 2)
                _tx['currency'] = item.currency
            
            if item.base_debit != 0 or cint(self.exclude_zero_sum_txs) == 0:     # if exclude zero, do not add this component
                transactions.append(totalise_key_currency(_tx))
             
        
        pinvs = self.get_docs([ref.__dict__ for ref in self.references], "Purchase Invoice")
        sql_query = """SELECT `tabPurchase Invoice`.`name`, 
                  `tabPurchase Invoice`.`posting_date`, 
                  `tabPurchase Invoice`.`currency`, 
                  `tabPurchase Invoice`.`grand_total` AS `credit`, 
                  `tabPurchase Invoice`.`base_grand_total` AS `base_credit`,
                  `tabPurchase Invoice`.`credit_to`,
                  `tabPurchase Invoice`.`net_total` AS `expense`,
                  `tabPurchase Invoice`.`base_net_total` AS `base_expense`, 
                  `tabPurchase Invoice`.`base_total_taxes_and_charges` AS `tax`, 
                  `tabPurchase Taxes and Charges`.`account_head`,
                  `tabPurchase Invoice`.`taxes_and_charges`,
                  `tabPurchase Taxes and Charges`.`rate`,
                  `tabPurchase Invoice`.`supplier_name`,
                  `tabPurchase Invoice`.`conversion_rate`
                FROM `tabPurchase Invoice`
                LEFT JOIN `tabPurchase Taxes and Charges` ON (`tabPurchase Invoice`.`name` = `tabPurchase Taxes and Charges`.`parent` AND  `tabPurchase Taxes and Charges`.`idx` = 1)
                WHERE `tabPurchase Invoice`.`name` IN ({pinvs});""".format(pinvs=self.get_sql_list(pinvs))
        
        pinv_items = frappe.db.sql(sql_query, as_dict=True)

        for item in pinv_items:
            # create item entries
            if item.taxes_and_charges:
                tax_record = frappe.get_doc("Purchase Taxes and Charges Template", item.taxes_and_charges)
                tax_code = tax_record.tax_code
            else:
                tax_code = None
            
            if item.supplier_name:
                text2 = html.escape(item.supplier_name)
            else:
                text2 = ""
            
            # find against accounts
            against_positions = []
            for account in frappe.db.sql("""
                SELECT 
                    `expense_account`, 
                    SUM(`base_net_amount`) AS `key_amount`, 
                    SUM(`net_amount`) AS `amount`
                FROM `tabPurchase Invoice Item`
                WHERE `parent` = "{pinv}"
                GROUP BY `expense_account`;""".format(pinv=item.name), as_dict=True):
                tax_amount = rounded((account['amount'] * (item.rate or 0) / 100), 2)
                against_positions.append({
                    'account': self.get_account_number(account['expense_account']),
                    'amount': rounded(account['amount'], 2),
                    'currency': item.currency,
                    'key_amount': rounded(account['key_amount'], 2),
                    'key_currency': base_currency,
                    'tax_amount': tax_amount,
                    'key_tax_amount': rounded((tax_amount * item.conversion_rate), 2)
                })
            # create content
            _tx = {
                'account': self.get_account_number(item.credit_to), 
                'amount': rounded(item.base_credit, 2), 
                'key_amount': rounded(item.base_credit, 2), 
                'key_currency': base_currency,
                'exchange_rate': item.conversion_rate,
                'against_singles': against_positions,
                'debit_credit': "C", 
                'date': item.posting_date, 
                'currency': base_currency, 
                'tax_account': self.get_account_number(item.account_head) or None, 
                # 'tax_amount': item.tax or None,    # this takes the complete tax amount
                # 'tax_amount': None,                  # calculate on the basis of the item
                # 'tax_amount': (item.base_credit * (item.rate or 0) / 100),
                'tax_rate': rounded(item.rate, 2) if item.rate else 0, 
                'tax_code': tax_code or "312", 
                'tax_currency': base_currency,
                'text1': html.escape(item.name),
                'text2': text2
            }
                
            if not restrict_currencies or item.currency in restrict_currencies:
                _tx['amount'] = rounded(item.credit, 2)
                _tx['currency'] = item.currency
            
            if item.base_debit != 0 or cint(self.exclude_zero_sum_txs) == 0:     # if exclude zero, do not add this component
                transactions.append(totalise_key_currency(_tx))
            
        # add payment entry transactions
        pes = self.get_docs([ref.__dict__ for ref in self.references], "Payment Entry")
        sql_query = """SELECT `tabPayment Entry`.`name`
                    FROM `tabPayment Entry`
                    WHERE`tabPayment Entry`.`name` IN ({pes})
            """.format(pes=self.get_sql_list(pes))

        pe_items = frappe.db.sql(sql_query, as_dict=True)
        
        # create item entries
        for item in pe_items:
            pe_record = frappe.get_doc("Payment Entry", item.name)
            if pe_record.payment_type == "Pay":
                debit_credit = "C"
            else:
                debit_credit = "D"
            # create content
            transaction = {
                'account': self.get_account_number(pe_record.paid_to),  # bank
                'amount': rounded(pe_record.paid_amount, 2), 
                'against_singles': [{
                    'account': self.get_account_number(pe_record.paid_from),    # debtor
                    'amount': rounded(pe_record.total_allocated_amount, 2),
                    'currency': pe_record.paid_from_account_currency,
                    'key_currency': base_currency,
                    'key_amount': rounded(pe_record.base_total_allocated_amount, 2)
                }],
                'debit_credit': debit_credit, 
                'date': pe_record.posting_date, 
                'currency': pe_record.paid_from_account_currency, 
                'key_currency': base_currency,
                'key_amount': rounded(pe_record.base_paid_amount, 2),
                'exchange_rate': pe_record.source_exchange_rate,
                'tax_account': None, 
                'tax_amount': None, 
                'tax_rate': 0, 
                'tax_code': None, 
                'text1': html.escape(pe_record.name)
            }
            # append deductions
            for deduction in pe_record.deductions:
                sign = 1
                if frappe.get_cached_value("Account", deduction.account, 'root_type') in ['Asset', 'Expense']:
                    sign = (-1)
                transaction['against_singles'].append({
                    'account': self.get_account_number(deduction.account),
                    'amount': rounded(sign * (deduction.amount / pe_record.source_exchange_rate), 2),    # virtual valuation to other currency
                    'currency': pe_record.paid_to_account_currency,
                    'key_amount': rounded(sign * deduction.amount, 2),
                    'key_currency': base_currency
                })
                
            # verify integrity
            sums = {'base': transaction['key_amount'], 'other': transaction['amount']}
            for s in transaction['against_singles']:
                sums['base'] -= s['key_amount']
                sums['other'] -= s['amount']
            
            if sums['base'] != 0:           # correct difference on last entry
                transaction['against_singles'][-1]['key_amount'] += sums['base']
            if sums['other'] != 0:           # correct difference on last entry
                transaction['against_singles'][-1]['amount'] += sums['other']
                
            # insert transaction
            transactions.append(transaction)  

        # add journal entry transactions
        jvs = self.get_docs([ref.__dict__ for ref in self.references], "Journal Entry")
        sql_query = """SELECT `tabJournal Entry`.`name`
                    FROM `tabJournal Entry`
                    WHERE`tabJournal Entry`.`name` IN ({jvs})
            """.format(jvs=self.get_sql_list(jvs))

        jv_items = frappe.db.sql(sql_query, as_dict=True)
        
        # create item entries
        for item in jv_items:
            jv_record = frappe.get_doc("Journal Entry", item.name)
            key_currency = frappe.get_cached_value("Company", jv_record.company, "default_currency")
            if jv_record.accounts[0].debit_in_account_currency != 0:
                debit_credit = "D"
                amount = jv_record.accounts[0].debit_in_account_currency
                key_amount = jv_record.accounts[0].debit
            else:
                debit_credit = "C"
                amount = jv_record.accounts[0].credit_in_account_currency
                key_amount = jv_record.accounts[0].credit
            # create content
            transaction = {
                'account': self.get_account_number(jv_record.accounts[0].account), 
                'amount': rounded(amount, 2), 
                'against_singles': [],
                'debit_credit': debit_credit, 
                'date': jv_record.posting_date, 
                'currency': jv_record.accounts[0].account_currency, 
                'tax_account': None, 
                'tax_amount': None, 
                'tax_rate': 0, 
                'tax_code': None, 
                'text1': html.escape(jv_record.name),
                'key_currency': key_currency,
                'key_amount': rounded(key_amount, 2)
            }
            if jv_record.multi_currency == 1:
                transaction['exchange_rate'] = jv_record.accounts[0].exchange_rate
                
            # append single accounts
            for i in range(1, len(jv_record.accounts), 1):
                if debit_credit == "D":
                    amount = jv_record.accounts[i].credit_in_account_currency - jv_record.accounts[i].debit_in_account_currency
                    key_amount = jv_record.accounts[i].credit - jv_record.accounts[i].debit
                else:
                    amount = jv_record.accounts[i].debit_in_account_currency - jv_record.accounts[i].credit_in_account_currency
                    key_amount = jv_record.accounts[i].debit - jv_record.accounts[i].credit
                transaction_single = {
                    'account': self.get_account_number(jv_record.accounts[i].account),
                    'amount': rounded(amount, 2),
                    'currency': jv_record.accounts[i].account_currency,
                    'key_currency': key_currency,
                    'key_amount': rounded(key_amount, 2)
                }
                if jv_record.multi_currency == 1:
                    transaction_single['exchange_rate'] = jv_record.accounts[i].exchange_rate

                transaction['against_singles'].append(transaction_single)
            # insert transaction
            transactions.append(transaction)  
                    
        return transactions        
        
def set_export_flag(dt, docs, exported):
    update_query = """
        UPDATE `tab{dt}`
        SET `tab{dt}`.`exported_to_abacus` = {exported}
        WHERE
            `tab{dt}`.`name` IN ({docs});""".format(dt=dt, docs=docs, exported=exported)
    frappe.db.sql(update_query)
    return
        
"""
Check debit and credit in key/base currency and if required, totalise using the last tax section (Abacus behaviour)
"""
def totalise_key_currency(tx):
    # initialise with debit/credit from collective node
    delta = tx.get("key_amount") or 0
    # subtract single nodes with tax
    for s in tx.get("against_singles"):
        delta -= ((s.get("key_amount") or 0) + (s.get("key_tax_amount") or 0))
        
    # add delta
    if delta != 0:
        tx['against_singles'][-1]['key_tax_amount'] = rounded((tx['against_singles'][-1].get("key_tax_amount") or 0 ) + delta, 2)
        
    return tx


"""
Compare a result file against the export xml to identify errors and take action
"""
@frappe.whitelist()
def compare_result_xml(docname, xml_content):
    # get the transaction xml file
    if not frappe.db.exists("Abacus Export File", docname):
        frappe.throw( _("Invalid Abacus File reference"), _("Error") )
        
    doc = frappe.get_doc("Abacus Export File", docname)
    transaction_xml = doc.render_transfer_file().get('content')
    
    # load both transfer file and result into BeautifulSoups
    # parse original transaction file
    transaction_soup = BeautifulSoup(transaction_xml, 'lxml')

    # find transactions
    export_transactions = transaction_soup.find_all('transaction')

    # extract id and text1 (=document number)
    export = {}
    for t in export_transactions:
        try:
            export[t['id']] = {
                'document': t.entry.collectiveinformation.text1.get_text(),
                'date': t.entry.collectiveinformation.entrydate.get_text()
            }
        except Exception as err:
            print("Transaction {0} has {1}".format(t['id'], err))
    
    # parse result file
    result_soup = BeautifulSoup(xml_content, 'lxml')

    # find transactions
    result_transactions = result_soup.find_all('transaction')

    # for each transaction, export ID and error message
    errors = []
    for t in result_transactions:
        errors.append({
            'id': t['id'],
            'error': t.messages.message.get_text()
        })
        
    # create a lookup table from document names to doctypes
    doctype_map = {}
    if doc.references:
        for r in doc.references:
            doctype_map[r.get('dn')] = r.get('dt')
    
    # extend the error list with doctypes and docnames
    for e in errors:
        try:
            e['document'] = export[e['id']]['document']
            e['date'] = export[e['id']]['date']
            e['doctype'] = doctype_map[e['document']]
            
        except Exception as err:
            e['document'] = "Not found"
            e['doctype'] = None
            e['date'] = None
            
    # render the output into a dialog
    output_dialog = frappe.render_template("erpnextswiss/erpnextswiss/doctype/abacus_export_file/compare_result_dialog.html", {'errors': errors})

    return output_dialog


"""
Download the xml content
"""
@frappe.whitelist()
def download_xml(docname):
    # get the transaction xml file
    if not frappe.db.exists("Abacus Export File", docname):
        frappe.throw( _("Invalid Abacus File reference"), _("Error") )
        
    doc = frappe.get_doc("Abacus Export File", docname)
    transaction_xml = doc.render_transfer_file().get('content')
    
    # return download
    frappe.local.response.filename = "{name}.xml".format(name=docname.replace(" ", "-").replace("/", "-"))
    frappe.local.response.filecontent = transaction_xml
    frappe.local.response.type = "download"
