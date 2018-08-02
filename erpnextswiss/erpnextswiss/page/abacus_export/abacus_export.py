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
        # add transactions
        sql_query = """SELECT 
                `tabGL Entry`.`posting_date` AS `posting_date`, 
                `tabGL Entry`.`debit` AS `debit`, 
                `tabGL Entry`.`credit` AS `credit`, 
                `tabGL Entry`.`account` AS `account`, 
                `tabGL Entry`.`account_currency` AS `account_currency`,
                `tabAccount`.`account_number` AS `account_number`,
                `tabGL Entry`.`voucher_type` AS `voucher_type`, 
                `tabGL Entry`.`voucher_no` AS `voucher_no`
            FROM `tabGL Entry`
            LEFT JOIN `tabAccount` ON `tabGL Entry`.`account` = `tabAccount`.`name`
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
            if item.debit:
                code = "D"
                value = item.debit
            else:
                code = "C"
                value = item.credit
            content += make_line("     <DebitCredit>{0}</DebitCredit>").format(code)
            content += make_line("     <Client></Client>")
            content += make_line("     <Division>0</Division>")
            content += make_line("     <KeyCurrency>{0}</KeyCurrency>").format(item.account_currency)
            content += make_line("     <EntryDate>{0}</EntryDate>").format(item.posting_date)
            content += make_line("     <ValueDate></ValueDate>")
            content += make_line("     <AmountData mode=\"SAVE\">")
            content += make_line("       <Currency>{0}</Currency>").format(item.account_currency)
            content += make_line("       <Amount>{0}</Amount>").format(value)
            content += make_line("     </AmountData>")
            content += make_line("     <KeyAmount>{0}</KeyAmount>").format(value)
            content += make_line("     <Account>{0}</Account>").format(item.account_number)
            content += make_line("     <IntercompanyId>0</IntercompanyId>")
            content += make_line("     <IntercompanyCode></IntercompanyCode>")
            content += make_line("     <Text1>Sammelbuchung</Text1>")
            content += make_line("     <DocumentNumber>{0}</DocumentNumber>").format(item.voucher_no)
            content += make_line("     <SingleCount>0</SingleCount>")
            content += make_line("    </CollectiveInformation>")
            content += make_line("    <SingleInformation mode=\"SAVE\">")
            content += make_line("      <Type>Normal</Type>")
            content += make_line("      <DebitCredit>{0}</DebitCredit>").format(code)
            content += make_line("      <EntryDate>{0}</EntryDate>").format(item.posting_date)
            content += make_line("      <ValueDate></ValueDate>")
            content += make_line("      <AmountData mode=\"SAVE\">")
            content += make_line("        <Currency>{0}</Currency>").format(item.account_currency)
            content += make_line("        <Amount>{0}</Amount>").format(value)
            content += make_line("      </AmountData>")
            content += make_line("      <KeyAmount>{0}</KeyAmount>").format(value)
            content += make_line("      <Account>2280</Account>")
            content += make_line("      <IntercompanyId>0</IntercompanyId>")
            content += make_line("      <IntercompanyCode></IntercompanyCode>")
            content += make_line("      <Text1>Sammelbuchung</Text1>")
            content += make_line("      <DocumentNumber>49377</DocumentNumber>")
            content += make_line("      <SelectionCode></SelectionCode>")
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
