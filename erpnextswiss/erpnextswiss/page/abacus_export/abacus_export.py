# -*- coding: utf-8 -*-
# Copyright (c) 2017-2019, libracore and contributors
# License: AGPL v3. See LICENCE
#
# NOTE: this is the old transfer method. 
# It is replaced by the Abacus Transfer File and will be deprecated soon
#

from __future__ import unicode_literals
import frappe
from frappe import throw, _
import hashlib
import six

@frappe.whitelist()
def generate_transfer_file(start_date, end_date, limit=10000, aggregated=0):
    # creates a transfer file for abacus

    #try:
        # normalise parameters
        aggregated = int(aggregated)
        limit = int(limit)
        # create xml header
        content = make_line("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        # define xml root node
        content += make_line("<AbaConnectContainer>")
        # control counter (TaskCount is actually the number of transactions)
        transaction_count = 0
        transaction_count_identifier = "<!-- $COUNT -->"
        content += make_line(" <TaskCount>{0}</TaskCount>".format(transaction_count_identifier))
        # task container
        content += make_line(" <Task>")
        # parameters
        content += make_line("  <Parameter>")
        content += make_line("   <Application>FIBU</Application>")
        content += make_line("   <Id>XML Buchungen</Id>")
        content += make_line("   <MapId>AbaDefault</MapId>")
        content += make_line("   <Version>2015.00</Version>")
        content += make_line("  </Parameter>")

        # add sales invoice transactions
        if aggregated == 1:
            sql_query = """SELECT `tabSales Invoice`.`name`, 
                  `tabSales Invoice`.`posting_date`, 
                  `tabSales Invoice`.`currency`, 
                  SUM(`tabSales Invoice`.`grand_total`) AS `debit`, 
                  `tabSales Invoice`.`debit_to`,
                  SUM(`tabSales Invoice`.`net_total`) AS `income`, 
                  `tabSales Invoice Item`.`income_account`,  
                  SUM(`tabSales Invoice`.`total_taxes_and_charges`) AS `tax`, 
                  `tabSales Taxes and Charges`.`account_head`,
                  `tabSales Invoice`.`taxes_and_charges`,
                  `tabSales Taxes and Charges`.`rate`,
                  "Various" AS `customer_name`,
                  CONCAT(IFNULL(`tabSales Invoice`.`debit_to`, ""),
                    IFNULL(`tabSales Invoice Item`.`income_account`, ""),  
                    IFNULL(`tabSales Taxes and Charges`.`account_head`, "")
                  ) AS `key`
                FROM `tabSales Invoice`
                LEFT JOIN `tabSales Invoice Item` ON `tabSales Invoice`.`name` = `tabSales Invoice Item`.`parent`
                LEFT JOIN `tabSales Taxes and Charges` ON `tabSales Invoice`.`name` = `tabSales Taxes and Charges`.`parent`
                WHERE
                    `tabSales Invoice`.`posting_date` >= '{start_date}'
                    AND `tabSales Invoice`.`posting_date` <= '{end_date}'
                    AND `tabSales Invoice`.`docstatus` = 1
                    AND `tabSales Invoice`.`exported_to_abacus` = 0
                GROUP BY `key`""".format(start_date=start_date, end_date=end_date)
        else:
            sql_query = """SELECT DISTINCT `tabSales Invoice`.`name`, 
                  `tabSales Invoice`.`posting_date`, 
                  `tabSales Invoice`.`currency`, 
                  `tabSales Invoice`.`grand_total` AS `debit`, 
                  `tabSales Invoice`.`debit_to`,
                  `tabSales Invoice`.`net_total` AS `income`, 
                  `tabSales Invoice Item`.`income_account`,  
                  `tabSales Invoice`.`total_taxes_and_charges` AS `tax`, 
                  `tabSales Taxes and Charges`.`account_head`,
                  `tabSales Invoice`.`taxes_and_charges`,
                  `tabSales Taxes and Charges`.`rate`,
                  `tabSales Invoice`.`customer_name`
                FROM `tabSales Invoice`
                LEFT JOIN `tabSales Invoice Item` ON `tabSales Invoice`.`name` = `tabSales Invoice Item`.`parent`
                LEFT JOIN `tabSales Taxes and Charges` ON (`tabSales Invoice`.`name` = `tabSales Taxes and Charges`.`parent` AND  `tabSales Taxes and Charges`.`idx` = 1)
                WHERE
                    `tabSales Invoice`.`posting_date` >= '{start_date}'
                    AND `tabSales Invoice`.`posting_date` <= '{end_date}'
                    AND `tabSales Invoice`.`docstatus` = 1
                    AND `tabSales Invoice`.`exported_to_abacus` = 0 
                LIMIT {limit}""".format(start_date=start_date, end_date=end_date, limit=limit)
        
        items = frappe.db.sql(sql_query, as_dict=True)
        
        if aggregated == 1:
            flag_sinvs_as_exportet = frappe.db.sql("""UPDATE `tabSales Invoice` SET `exported_to_abacus` = 1 WHERE `posting_date` >= '{start_date}' AND `posting_date` <= '{end_date}' AND `docstatus` = 1 AND `exported_to_abacus` = 0""".format(start_date=start_date, end_date=end_date), as_list=True)
        else:
            sinv_range = []
            for sinv in items:
                sinv_range.append(sinv.name)
        
        # mark all entries as exported
            export_matches = frappe.get_all("Sales Invoice", filters=[
                ["posting_date",">=", start_date],
                ["posting_date","<=", end_date],
                ["docstatus","=", 1],
                ["name","in", sinv_range],
                ["exported_to_abacus","=",0]], fields=['name'])
            for export_match in export_matches:
                record = frappe.get_doc("Sales Invoice", export_match['name'])
                record.exported_to_abacus = 1
                record.save(ignore_permissions=True)
        # create item entries
        transaction_count = 0
        for item in items:
            if aggregated == 1:
                date = end_date
            else:
                date = item.posting_date
            if item.taxes_and_charges:
                tax_record = frappe.get_doc("Sales Taxes and Charges Template", item.taxes_and_charges)
                # create content block with taxes
                content += add_transaction_block(account=item.debit_to, amount=item.debit, 
                    against_account=item.income_account, against_amount=item.income, 
                    debit_credit="D", date=date, currency=item.currency, transaction_count=transaction_count, 
                    tax_account=item.account_head, tax_amount=item.tax, tax_rate=item.rate, 
                    tax_code=tax_record.tax_code or "312", doc_ref=item.name,
                    doc_text=item.customer_name)
            else:
                # create content block without taxes
                content += add_transaction_block(account=item.debit_to, amount=item.debit, 
                    against_account=item.income_account, against_amount=item.income, 
                    debit_credit="D", date=date, currency=item.currency, transaction_count=transaction_count,
                    tax_account=None, tax_amount=None, tax_rate=None, tax_code=None, doc_ref=item.name,
                    doc_text=item.customer_name)

            transaction_count += 1        
        
        # add purchase invoice transactions
        if aggregated == 1:
            sql_query = """SELECT `tabPurchase Invoice`.`name`, 
                  `tabPurchase Invoice`.`posting_date`, 
                  `tabPurchase Invoice`.`currency`, 
                  SUM(`tabPurchase Invoice`.`grand_total`) AS `debit`, 
                  `tabPurchase Invoice`.`credit_to`,
                  SUM(`tabPurchase Invoice`.`net_total`) AS `income`, 
                  `tabPurchase Invoice Item`.`expense_account`,  
                  SUM(`tabPurchase Invoice`.`total_taxes_and_charges`) AS `tax`, 
                  `tabPurchase Taxes and Charges`.`account_head`,
                  `tabPurchase Invoice`.`taxes_and_charges`,
                  `tabPurchase Taxes and Charges`.`rate`,
                  "Various" AS `supplier_name`,
                  CONCAT(IFNULL(`tabPurchase Invoice`.`debit_to`, ""),
                    IFNULL(`tabPurchase Invoice Item`.`income_account`, ""),  
                    IFNULL(`tabPurchase Taxes and Charges`.`account_head`, "")
                  ) AS `key`
                FROM `tabPurchase Invoice`
                LEFT JOIN `tabPurchase Invoice Item` ON `tabPurchase Invoice`.`name` = `tabPurchase Invoice Item`.`parent`
                LEFT JOIN `tabPurchase Taxes and Charges` ON `tabPurchase Invoice`.`name` = `tabPurchase Taxes and Charges`.`parent`
                WHERE
                    `tabPurchase Invoice`.`posting_date` >= '{start_date}'
                    AND `tabPurchase Invoice`.`posting_date` <= '{end_date}'
                    AND `tabPurchase Invoice`.`docstatus` = 1
                    AND `tabPurchase Invoice`.`exported_to_abacus` = 0
                GROUP BY `key`""".format(start_date=start_date, end_date=end_date)
        else:
            sql_query = """SELECT DISTINCT `tabPurchase Invoice`.`name`, 
                  `tabPurchase Invoice`.`posting_date`, 
                  `tabPurchase Invoice`.`currency`, 
                  `tabPurchase Invoice`.`grand_total` AS `debit`, 
                  `tabPurchase Invoice`.`credit_to`,
                  `tabPurchase Invoice`.`net_total` AS `income`, 
                  `tabPurchase Invoice Item`.`expense_account`,  
                  `tabPurchase Invoice`.`total_taxes_and_charges` AS `tax`, 
                  `tabPurchase Taxes and Charges`.`account_head`,
                  `tabPurchase Invoice`.`taxes_and_charges`,
                  `tabPurchase Taxes and Charges`.`rate`,
                  `tabPurchase Invoice`.`supplier_name`
                FROM `tabPurchase Invoice`
                LEFT JOIN `tabPurchase Invoice Item` ON `tabPurchase Invoice`.`name` = `tabPurchase Invoice Item`.`parent`
                LEFT JOIN `tabPurchase Taxes and Charges` ON (`tabPurchase Invoice`.`name` = `tabPurchase Taxes and Charges`.`parent` AND  `tabPurchase Taxes and Charges`.`idx` = 1)
                WHERE
                    `tabPurchase Invoice`.`posting_date` >= '{start_date}'
                    AND `tabPurchase Invoice`.`posting_date` <= '{end_date}'
                    AND `tabPurchase Invoice`.`docstatus` = 1
                    AND `tabPurchase Invoice`.`exported_to_abacus` = 0 
                LIMIT {limit}""".format(start_date=start_date, end_date=end_date, limit=limit)
        
        items = frappe.db.sql(sql_query, as_dict=True)
        
        if aggregated == 1:
            flag_sinvs_as_exportet = frappe.db.sql("""UPDATE `tabPurchase Invoice` SET `exported_to_abacus` = 1 WHERE `posting_date` >= '{start_date}' AND `posting_date` <= '{end_date}' AND `docstatus` = 1 AND `exported_to_abacus` = 0""".format(start_date=start_date, end_date=end_date), as_list=True)
        else:
            sinv_range = []
            for sinv in items:
                sinv_range.append(sinv.name)
        
        # mark all entries as exported
            export_matches = frappe.get_all("Purchase Invoice", filters=[
                ["posting_date",">=", start_date],
                ["posting_date","<=", end_date],
                ["docstatus","=", 1],
                ["name","in", sinv_range],
                ["exported_to_abacus","=",0]], fields=['name'])
            for export_match in export_matches:
                record = frappe.get_doc("Purchase Invoice", export_match['name'])
                record.exported_to_abacus = 1
                record.save(ignore_permissions=True)
        # create item entries
        transaction_count = 0
        for item in items:
            if aggregated == 1:
                date = end_date
            else:
                date = item.posting_date
            if item.taxes_and_charges:
                tax_record = frappe.get_doc("Purchase Taxes and Charges Template", item.taxes_and_charges)
                # create content block with taxes
                content += add_transaction_block(account=item.debit_to, amount=item.debit, 
                    against_account=item.income_account, against_amount=item.income, 
                    debit_credit="D", date=date, currency=item.currency, transaction_count=transaction_count, 
                    tax_account=item.account_head, tax_amount=item.tax, tax_rate=item.rate, 
                    tax_code=tax_record.tax_code or "312", doc_ref=item.name,
                    doc_text=item.supplier_name)
            else:
                # create content block without taxes
                content += add_transaction_block(account=item.debit_to, amount=item.debit, 
                    against_account=item.income_account, against_amount=item.income, 
                    debit_credit="D", date=date, currency=item.currency, transaction_count=transaction_count,
                    tax_account=None, tax_amount=None, tax_rate=None, tax_code=None, doc_ref=item.name,
                    doc_text=item.supplier_name)

            transaction_count += 1      
            
        # add payment entry transactions
        if aggregated == 1:
            sql_query = """SELECT `tabPayment Entry`.`name`,
                      `tabPayment Entry`.`posting_date`, 
                      `tabPayment Entry`.`paid_from_account_currency` AS `currency`,
                      SUM(`tabPayment Entry`.`paid_amount`) AS `amount`, 
                      `tabPayment Entry`.`paid_from`,
                      `tabPayment Entry`.`paid_to`,
                      CONCAT(IFNULL(`tabPayment Entry`.`paid_from`, ""),
                        IFNULL(`tabPayment Entry`.`paid_to`, "")
                      ) AS `key`
                    FROM `tabPayment Entry`
                    WHERE
                        `posting_date` >= '{start_date}'
                        AND `posting_date` <= '{end_date}'
                        AND `docstatus` = 1
                        AND `exported_to_abacus` = 0
                    GROUP BY `key`
                """.format(start_date=start_date, end_date=end_date)
        else:
            sql_query = """SELECT `tabPayment Entry`.`name`,
                      `tabPayment Entry`.`posting_date`, 
                      `tabPayment Entry`.`paid_from_account_currency` AS `currency`,
                      `tabPayment Entry`.`paid_amount` AS `amount`, 
                      `tabPayment Entry`.`paid_from`,
                      `tabPayment Entry`.`paid_to`,
                      CONCAT(IFNULL(`tabPayment Entry`.`paid_from`, ""),
                        IFNULL(`tabPayment Entry`.`paid_to`, "")
                      ) AS `key`
                    FROM `tabPayment Entry`
                    WHERE
                        `posting_date` >= '{start_date}'
                        AND `posting_date` <= '{end_date}'
                        AND `docstatus` = 1
                        AND `exported_to_abacus` = 0
                LIMIT {limit}""".format(start_date=start_date, end_date=end_date, limit=limit)

        items = frappe.db.sql(sql_query, as_dict=True)
        if aggregated == 1:
            flag_sinvs_as_exportet = frappe.db.sql("""UPDATE `tabPayment Entry` SET `exported_to_abacus` = 1 WHERE `posting_date` >= '{start_date}' AND `posting_date` <= '{end_date}' AND `docstatus` = 1 AND `exported_to_abacus` = 0""".format(start_date=start_date, end_date=end_date), as_list=True)
        else:
            payment_range = []
            for payment in items:
                payment_range.append(payment.name)
            # mark all entries as exported
            export_matches = frappe.get_all("Payment Entry", filters=[
                ["posting_date",">=", start_date],
                ["posting_date","<=", end_date],
                ["docstatus","=", 1],
                ["name","in", payment_range],
                ["exported_to_abacus","=",0]], fields=['name'])
            for export_match in export_matches:
                record = frappe.get_doc("Payment Entry", export_match['name'])
                record.exported_to_abacus = 1
                record.save(ignore_permissions=True)
		
        # create item entries
        for item in items:
            if aggregated == 1:
                date = end_date
            else:
                date = item.posting_date
            # create content block
            content += add_transaction_block(account=item.paid_from, amount=item.amount, 
                against_account=item.paid_to, against_amount=item.amount, 
                debit_credit="C", date=date, currency=item.currency, transaction_count=transaction_count,
                tax_account=None, tax_amount=None, tax_rate=None, tax_code=None, doc_ref=item.name)

            transaction_count += 1

        # add footer
        content += make_line(" </Task>")
        content += make_line("</AbaConnectContainer>")
        # insert control numbers
        content = content.replace(transaction_count_identifier, "{0}".format(transaction_count))

        # create a log entry for debug
        frappe.log_error(content, "Abacus export content")

        return { 'content': content }
    #except:
    #    frappe.throw( _("Error while generating xml. Make sure that you made required customisations to the DocTypes.") )
    #    return

# Params
#  debit_credit: "D" or "C"
def add_transaction_block(account, amount, against_account, against_amount, 
        debit_credit, date, currency, transaction_count, tax_account=None, 
        tax_amount=None, tax_rate=None, tax_code=None, doc_ref="Sammelbuchung", doc_text=None):
    date_str = six.text_type(date)
    transaction_reference = "{0} {1} {2} {3}".format(date_str, account, debit_credit, amount)
    short_reference = "{0}{1}{2}{3}".format(date_str[2:4], date_str[5:7], date_str[8:10], transaction_count)
    content = make_line("  <Transaction id=\"{0}\">").format(transaction_count)
    content += make_line("   <Entry mode=\"SAVE\">")
    content += make_line("    <CollectiveInformation mode=\"SAVE\">")
    content += make_line("     <EntryLevel>A</EntryLevel>")
    content += make_line("     <EntryType>S</EntryType>")
    content += make_line("     <Type>Normal</Type>")
    content += make_line("     <DebitCredit>{0}</DebitCredit>".format(debit_credit))
    content += make_line("     <Client></Client>")              # customer number
    content += make_line("     <Division>0</Division>")
    content += make_line("     <KeyCurrency>{0}</KeyCurrency>".format(currency))
    content += make_line("     <EntryDate>{0}</EntryDate>".format(date))
    content += make_line("     <ValueDate></ValueDate>")
    content += make_line("     <AmountData mode=\"SAVE\">")
    content += make_line("      <Currency>{0}</Currency>".format(currency))
    content += make_line("      <Amount>{0}</Amount>".format(amount))
    content += make_line("     </AmountData>")
    content += make_line("     <KeyAmount>{0}</KeyAmount>".format(amount))
    content += make_line("     <Account>{0}</Account>".format(get_account_number(account)))
    content += make_line("     <IntercompanyId>0</IntercompanyId>")
    content += make_line("     <IntercompanyCode></IntercompanyCode>")
    content += make_line("     <Text1>{0}</Text1>".format(doc_ref))
    if doc_text:
        content += make_line("     <Text2>{0}</Text2>".format(doc_text))
    content += make_line("     <DocumentNumber>{0}</DocumentNumber>".format(short_reference))
    content += make_line("     <SingleCount>0</SingleCount>")
    content += make_line("    </CollectiveInformation>")
    content += make_line("    <SingleInformation mode=\"SAVE\">")
    content += make_line("     <Type>Normal</Type>")
    content += make_line("     <DebitCredit>{0}</DebitCredit>".format(debit_credit))
    content += make_line("     <EntryDate>{0}</EntryDate>".format(date))
    content += make_line("     <ValueDate></ValueDate>")
    content += make_line("     <AmountData mode=\"SAVE\">")
    content += make_line("      <Currency>{0}</Currency>".format(currency))
    content += make_line("      <Amount>{0}</Amount>".format(amount))
    content += make_line("     </AmountData>")
    content += make_line("     <KeyAmount>{0}</KeyAmount>".format(amount))
    content += make_line("     <Account>{0}</Account>".format(get_account_number(against_account)))
    if tax_account:
        content += make_line("     <TaxAccount>{0}</TaxAccount>".format(get_account_number(tax_account)))
    content += make_line("     <IntercompanyId>0</IntercompanyId>")
    content += make_line("     <IntercompanyCode></IntercompanyCode>")
    content += make_line("     <Text1>{0}</Text1>".format(doc_ref))
    content += make_line("     <DocumentNumber>{0}</DocumentNumber>".format(short_reference))
    content += make_line("     <SelectionCode></SelectionCode>")
    if tax_account:
        content += make_line("     <TaxData mode=\"SAVE\">")
        content += make_line("      <TaxIncluded>I</TaxIncluded>")
        content += make_line("      <TaxType>1</TaxType>")
        content += make_line("      <UseCode>1</UseCode>")
        content += make_line("      <AmountData mode=\"SAVE\">")
        content += make_line("       <Currency>{0}</Currency>".format(currency))
        content += make_line("       <Amount>0</Amount>")
        content += make_line("      </AmountData>")
        content += make_line("      <KeyAmount>{0}</KeyAmount>".format(tax_amount * (-1)))
        content += make_line("      <TaxRate>{0}</TaxRate>").format(tax_rate)
        content += make_line("      <TaxCoefficient>100</TaxCoefficient>")
        content += make_line("      <Country>CH</Country>")
        content += make_line("      <TaxCode>{0}</TaxCode>".format(tax_code))
        content += make_line("      <Number></Number>")
        content += make_line("      <FlatRate>0</FlatRate>")
        content += make_line("     </TaxData>")
    content += make_line("    </SingleInformation>")
    content += make_line("   </Entry>")
    content += make_line("  </Transaction>")
    return content

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"

# returns the account number of an account
def get_account_number(account_name):
    sql_query = """SELECT 
            `account_number`
        FROM `tabAccount`
        WHERE
            `name` = '{account_name}'
        LIMIT 1
        """.format(account_name=account_name)
    items = frappe.db.sql(sql_query, as_dict=True)
    if items:
        return items[0]['account_number']
    else:
        return None

# returns the first income account number for a sales invoice
def get_income_account_number(sales_invoice):
    sql_query = """SELECT 
            `tabAccount`.`account_number` AS `account_number`
        FROM `tabSales Invoice Item`
        LEFT JOIN `tabAccount` ON `tabSales Invoice Item`.`income_account` = `tabAccount`.`name`
        WHERE
            `tabSales Invoice Item`.`parent` = '{sales_invoice}'
        LIMIT 1
        """.format(sales_invoice=sales_invoice)
    items = frappe.db.sql(sql_query, as_dict=True)
    if items:
        return items[0]['account_number']
    else:
        return None
        
def get_sales_taxes(sales_invoice):
    sql_query = """SELECT 
            `tabSales Taxes and Charges`.`rate` AS `rate`,
            `tabSales Taxes and Charges`.`tax_amount` AS `tax_amount`,
            `tabAccount`.`account_number` AS `account_number`
        FROM `tabSales Taxes and Charges`
        LEFT JOIN `tabAccount` ON `tabSales Taxes and Charges`.`account_head` = `tabAccount`.`name`
        WHERE
            `tabSales Taxes and Charges`.`parent` = '{sales_invoice}'
        LIMIT 1
        """.format(sales_invoice=sales_invoice)
    items = frappe.db.sql(sql_query, as_dict=True)
    if items:
        return items[0]
    else:
        return None

# this will reset the export flags
@frappe.whitelist()
def reset_export_flags():
    sql_query = """UPDATE `tabGL Entry` SET `exported_to_abacus` = 0;"""
    frappe.db.sql(sql_query, as_dict=True)
    sql_query = """UPDATE `tabSales Invoice` SET `exported_to_abacus` = 0;"""
    frappe.db.sql(sql_query, as_dict=True)
    sql_query = """UPDATE `tabPayment Entry` SET `exported_to_abacus` = 0;"""
    frappe.db.sql(sql_query, as_dict=True)
    sql_query = """UPDATE `tabPurchase Invoice` SET `exported_to_abacus` = 0;"""
    frappe.db.sql(sql_query, as_dict=True)
    return { 'message': 'OK' }

# get transactions
@frappe.whitelist()
def get_transactions(start_date, end_date):
    sql_query = """SELECT `posting_date` AS `date`, `debit_to` AS `account`, `name`, `base_grand_total` AS `amount`, "Sales Invoice" AS `type` 
        FROM `tabSales Invoice`
        WHERE
            `posting_date` >= '{start_date}'
            AND `posting_date` <= '{end_date}'
            AND `docstatus` = 1
            AND `exported_to_abacus` = 0
        UNION SELECT `posting_date` AS `date`, `paid_to` AS `account`, `name`, `paid_amount` AS `amount`, "Payment Entry" AS `type`
        FROM `tabPayment Entry`
        WHERE
            `posting_date` >= '{start_date}'
            AND `posting_date` <= '{end_date}'
            AND `docstatus` = 1
            AND `exported_to_abacus` = 0
        ORDER BY `date` LIMIT 20""".format(start_date=start_date, end_date=end_date)
    items = frappe.db.sql(sql_query, as_dict=True)
    if items:
        return items
    else:
        return None
