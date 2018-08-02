# -*- coding: utf-8 -*-
# Copyright (c) 2017-2018, libracore and contributors
# License: AGPL v3. See LICENCE

from __future__ import unicode_literals
import frappe
from frappe import throw, _

@frappe.whitelist()
def generate_transfer_file(start_date, end_date):
    # creates a transfer file for abacus

    #try:        
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
        sql_query = """SELECT 
                `name`,
                `posting_date`,
                `debit_to`,
                `currency`,
                `grand_total`
            FROM `tabSales Invoice`
            WHERE
            	`posting_date` >= '{start_date}'
				AND `posting_date` <= '{end_date}'
				AND `docstatus` = 1
            """.format(start_date=start_date, end_date=end_date)
        items = frappe.db.sql(sql_query, as_dict=True)
        for item in items:
            transaction_count += 1
            content += make_line("  <Transaction id=\"{0}\">").format(transaction_count)
            content += make_line("    <Entry mode=\"SAVE\">")
            content += make_line("    <CollectiveInformation mode=\"SAVE\">")
            content += make_line("     <EntryLevel>A</EntryLevel>")
            content += make_line("     <EntryType>S</EntryType>")
            content += make_line("     <Type>Normal</Type>")
            content += make_line("     <DebitCredit>D</DebitCredit>")
            content += make_line("     <Client></Client>")              # customer number
            content += make_line("     <Division>0</Division>")
            content += make_line("     <KeyCurrency>{0}</KeyCurrency>").format(item.currency)
            content += make_line("     <EntryDate>{0}</EntryDate>").format(item.posting_date)
            content += make_line("     <ValueDate></ValueDate>")
            content += make_line("     <AmountData mode=\"SAVE\">")
            content += make_line("      <Currency>{0}</Currency>").format(item.currency)
            content += make_line("      <Amount>{0}</Amount>").format(item.grand_total)
            content += make_line("     </AmountData>")
            content += make_line("     <KeyAmount>{0}</KeyAmount>").format(item.grand_total)
            content += make_line("     <Account>{0}</Account>").format(get_account_number(item.debit_to))
            content += make_line("     <IntercompanyId>0</IntercompanyId>")
            content += make_line("     <IntercompanyCode></IntercompanyCode>")
            content += make_line("     <Text1>Sammelbuchung</Text1>")
            content += make_line("     <DocumentNumber>{0}</DocumentNumber>").format(item.name)
            content += make_line("     <SingleCount>0</SingleCount>")
            content += make_line("    </CollectiveInformation>")
            content += make_line("    <SingleInformation mode=\"SAVE\">")
            content += make_line("     <Type>Normal</Type>")
            content += make_line("     <DebitCredit>D</DebitCredit>")
            content += make_line("     <EntryDate>{0}</EntryDate>").format(item.posting_date)
            content += make_line("     <ValueDate></ValueDate>")
            content += make_line("     <AmountData mode=\"SAVE\">")
            content += make_line("      <Currency>{0}</Currency>").format(item.currency)
            content += make_line("      <Amount>{0}</Amount>").format(item.grand_total)
            content += make_line("     </AmountData>")
            content += make_line("     <KeyAmount>{0}</KeyAmount>").format(item.grand_total)
            content += make_line("     <Account>{0}</Account>").format(get_income_account_number(item.name))
            taxes = get_sales_taxes(item.name)
            if taxes:
                content += make_line("     <TaxAccount>{0}</TaxAccount>").format(taxes.account_number)
            content += make_line("     <IntercompanyId>0</IntercompanyId>")
            content += make_line("     <IntercompanyCode></IntercompanyCode>")
            content += make_line("     <BookingLevel1>650</BookingLevel1>")
            content += make_line("     <Text1>Sammelbuchung</Text1>")
            content += make_line("     <DocumentNumber>{0}</DocumentNumber>").format(item.name)
            content += make_line("     <SelectionCode></SelectionCode>")
            if taxes:
                content += make_line("     <TaxData mode=\"SAVE\">")
                content += make_line("      <TaxIncluded>I</TaxIncluded>")
                content += make_line("      <TaxType>1</TaxType>")
                content += make_line("      <UseCode>1</UseCode>")
                content += make_line("      <AmountData mode=\"SAVE\">")
                content += make_line("       <Currency>{0}</Currency>").format(item.currency)
                content += make_line("       <Amount>0</Amount>")
                content += make_line("      </AmountData>")
                content += make_line("      <KeyAmount>-{0}</KeyAmount>").format(taxes.tax_amount)
                content += make_line("      <TaxRate>{0}</TaxRate>").format(taxes.rate)
                content += make_line("      <TaxCoefficient>100</TaxCoefficient>")
                content += make_line("      <Country>CH</Country>")
                content += make_line("      <TaxCode>312</TaxCode>")
                content += make_line("      <Number></Number>")
                content += make_line("      <FlatRate>0</FlatRate>")
                content += make_line("     </TaxData>")
            content += make_line("    </SingleInformation>")
            content += make_line("   </Entry>")
            content += make_line("  </Transaction>")
        # add payment entry transactions
        sql_query = """SELECT 
                `name`, 
                `paid_from_account_currency` AS `currency`, 
                `posting_date`,
                `paid_amount`,
                `paid_to`,
                `paid_from`
            FROM `tabPayment Entry`
            WHERE
            	`posting_date` >= '{start_date}'
				AND `posting_date` <= '{end_date}'
				AND `docstatus` = 1
            """.format(start_date=start_date, end_date=end_date)
        items = frappe.db.sql(sql_query, as_dict=True)
        for item in items:
            transaction_count += 1        
            content += make_line("  <Transaction id=\"{0}\">").format(transaction_count)
            content += make_line("   <Entry mode=\"SAVE\">")
            content += make_line("    <CollectiveInformation mode=\"SAVE\">")
            content += make_line("     <EntryLevel>A</EntryLevel>")
            content += make_line("     <EntryType>S</EntryType>")
            content += make_line("     <Type>Normal</Type>")
            content += make_line("     <DebitCredit>D</DebitCredit>")
            content += make_line("     <Client></Client>")              # customer number
            content += make_line("     <Division>0</Division>")
            content += make_line("     <KeyCurrency>{0}</KeyCurrency>").format(item.currency)
            content += make_line("     <EntryDate>{0}</EntryDate>").format(item.posting_date)
            content += make_line("     <ValueDate></ValueDate>")
            content += make_line("     <AmountData mode=\"SAVE\">")
            content += make_line("      <Currency>{0}</Currency>").format(item.currency)
            content += make_line("      <Amount>{0}</Amount>").format(item.paid_amount)
            content += make_line("     </AmountData>")
            content += make_line("     <KeyAmount>{0}</KeyAmount>").format(item.paid_amount)
            content += make_line("     <Account>{0}</Account>").format(get_account_number(item.paid_to))
            content += make_line("     <IntercompanyId>0</IntercompanyId>")
            content += make_line("     <IntercompanyCode></IntercompanyCode>")
            content += make_line("     <Text1>Sammelbuchung</Text1>")
            content += make_line("     <DocumentNumber>{0}</DocumentNumber>").format(item.name)
            content += make_line("     <SingleCount>0</SingleCount>")
            content += make_line("    </CollectiveInformation>")
            content += make_line("    <SingleInformation mode=\"SAVE\">")
            content += make_line("     <Type>Normal</Type>")
            content += make_line("     <DebitCredit>D</DebitCredit>")
            content += make_line("     <EntryDate>{0}</EntryDate>").format(item.posting_date)
            content += make_line("     <ValueDate></ValueDate>")
            content += make_line("     <AmountData mode=\"SAVE\">")
            content += make_line("      <Currency>{0}</Currency>").format(item.currency)
            content += make_line("      <Amount>{0}</Amount>").format(item.paid_amount)
            content += make_line("     </AmountData>")
            content += make_line("     <KeyAmount>{0}</KeyAmount>").format(item.paid_amount)
            content += make_line("     <Account>{0}</Account>").format(get_account_number(item.paid_from))
            content += make_line("     <IntercompanyId>0</IntercompanyId>")
            content += make_line("     <IntercompanyCode></IntercompanyCode>")
            content += make_line("     <Text1>Sammelbuchung</Text1>")
            content += make_line("     <DocumentNumber>{0}</DocumentNumber>").format(item.name)
            content += make_line("     <SelectionCode></SelectionCode>")
            content += make_line("    </SingleInformation>")
            content += make_line("   </Entry>")
            content += make_line("  </Transaction>")
        # add footer
        content += make_line(" </Task>")
        content += make_line("</AbaConnectContainer>")
        # insert control numbers
        content = content.replace(transaction_count_identifier, "{0}".format(transaction_count))
        
        return { 'content': content }
    #except IndexError:
    #    frappe.msgprint( _("Please select at least one payment."), _("Information") )
    #    return
    #except:
    #    frappe.throw( _("Error while generating xml. Make sure that you made required customisations to the DocTypes.") )
    #    return

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
