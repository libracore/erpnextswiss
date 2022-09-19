# -*- coding: utf-8 -*-
# Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
import time
from erpnextswiss.erpnextswiss.common_functions import get_building_number, get_street_name, get_pincode, get_city, get_primary_address
import html          # used to escape xml content
from frappe.utils import cint, get_url_to_form
from unidecode import unidecode     # used to remove German/French-type special characters from bank identifieres

class PaymentProposal(Document):
    def validate(self):
        # check company settigs
        company_address = get_primary_address(target_name=self.company, target_type="Company")
        if (not company_address
            or not company_address.address_line1
            or not company_address.pincode
            or not company_address.city):
                frappe.throw( _("Company address missing or incomplete.") )
        if self.pay_from_account:
            payment_account = frappe.get_doc('Account', self.pay_from_account)
            if not payment_account.iban:
                frappe.throw( _("IBAN missing in pay from account.") )
        # perform some checks to improve file quality/stability
        for purchase_invoice in self.purchase_invoices: 
            pinv = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
            # check addresses (mandatory in ISO 20022
            if not pinv.supplier_address:
                frappe.throw( _("Address missing for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
            # check target account info
            if purchase_invoice.payment_type == "ESR":
                if not purchase_invoice.esr_reference or not purchase_invoice.esr_participation_number:
                    frappe.throw( _("ESR: missing transaction information (participant number or reference) in <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
            else:
                supl = frappe.get_doc("Supplier", pinv.supplier)
                if not supl.iban:
                    frappe.throw( _("Missing IBAN for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
        # check expense records
        for expense_claim in self.expenses:
            emp = frappe.get_doc("Employee", expense_claim.employee)
            if not emp.bank_ac_no:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no bank account number.").format(emp.name) )
        return
        
    def on_submit(self):
        # clean payments (to prevent accumulation on re-submit)
        self.payments = {}
        # create the aggregated payment table
        # collect customers
        suppliers = []
        total = 0
        for purchase_invoice in self.purchase_invoices:
            if purchase_invoice.supplier not in suppliers:
                suppliers.append(purchase_invoice.supplier)
        # aggregate purchase invoices
        for supplier in suppliers:
            amount = 0
            references = []
            currency = ""
            address = ""
            payment_type = "SEPA"
            # try executing in 90 days (will be reduced by actual due dates)
            exec_date = datetime.strptime(self.date, "%Y-%m-%d") + timedelta(days=90)
            for purchase_invoice in self.purchase_invoices:
                if purchase_invoice.supplier == supplier:
                    currency = purchase_invoice.currency
                    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    address = pinv.supplier_address
                    references.append(purchase_invoice.external_reference)
                    # find if skonto applies
                    if purchase_invoice.skonto_date:
                        skonto_date = datetime.strptime(purchase_invoice.skonto_date, "%Y-%m-%d")
                    due_date = datetime.strptime(purchase_invoice.due_date, "%Y-%m-%d")
                    if (purchase_invoice.skonto_date) and (skonto_date.date() >= datetime.now().date()):  
                        this_amount = purchase_invoice.skonto_amount    
                        if exec_date.date() > skonto_date.date():
                            exec_date = skonto_date
                    else:
                        this_amount = purchase_invoice.amount
                        if exec_date.date() > due_date.date():
                            exec_date = due_date
                    payment_type = purchase_invoice.payment_type
                    if payment_type == "ESR" or self.individual_payments == 1:
                        # run as individual payment (not aggregated)
                        supl = frappe.get_doc("Supplier", supplier)
                        addr = frappe.get_doc("Address", address)
                        self.add_payment(supl.supplier_name, supl.iban, payment_type,
                            addr.address_line1, "{0} {1}".format(addr.pincode, addr.city), addr.country,
                            this_amount, currency, purchase_invoice.external_reference, skonto_date or due_date, 
                            purchase_invoice.esr_reference, purchase_invoice.esr_participation_number, bic=supl.bic)
                        total += this_amount
                    else:
                        amount += this_amount
                    # mark sales invoices as proposed
                    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        self.create_payment("Supplier", supplier, 
                            "Purchase Invoice", purchase_invoice.purchase_invoice, exec_date,
                            purchase_invoice.amount, bic=supl.bic)
            # make sure execution date is valid
            if exec_date < datetime.now():
                exec_date = datetime.now()      # + timedelta(days=1)
            # add new payment record
            if amount > 0:
                supl = frappe.get_doc("Supplier", supplier)
                addr = frappe.get_doc("Address", address)
                if payment_type == "ESR":           # prevent if last invoice was by ESR, but others are also present -> pay as IBAN
                    payment_type = "IBAN"
                self.add_payment(supl.supplier_name, supl.iban, payment_type,
                    addr.address_line1, "{0} {1}".format(addr.pincode, addr.city), addr.country,
                    amount, currency, " ".join(references), exec_date, bic=supl.bic)
                total += amount
        # collect employees
        employees = []
        account_currency = frappe.get_value("Account", self.pay_from_account, 'account_currency')
        for expense_claim in self.expenses:
            if expense_claim.employee not in employees:
                employees.append(expense_claim.employee)
        # aggregate expense claims
        for employee in employees:
            amount = 0
            references = []
            currency = ""
            for expense_claim in self.expenses:
                if expense_claim.employee == employee:
                    amount += expense_claim.amount
                    currency = account_currency
                    references.append(expense_claim.expense_claim)
                    # mark expense claim as proposed
                    invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        self.create_payment("Employee", employee, 
                            "Expense Claim", expense_claim.expense_claim, exec_date,
                            expense_claim.amount)
            # add new payment record
            emp = frappe.get_doc("Employee", employee)
            if not emp.permanent_address:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no address.").format(emp.name) )
            address_lines = emp.permanent_address.split("\n")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(emp.employee_name, emp.bank_ac_no, "IBAN",
                address_lines[0], address_lines[1], cntry,
                amount, currency, " ".join(references), self.date)
            total += amount
        # add salaries
        for salary in self.salaries:
            # mark expense claim as proposed
            salary_slip = frappe.get_doc("Salary Slip", salary.salary_slip)
            salary_slip.is_proposed = 1
            salary_slip.save()
            # create payment on intermediate
            if self.use_intermediate == 1:
                self.create_payment("Employee", employee, 
                    "Salary Slip", salary.salary_slip, exec_date,
                    salary.amount)
            # add new payment record
            emp = frappe.get_doc("Employee", salary.employee)
            if not emp.permanent_address:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no address.").format(emp.name) )
            address_lines = emp.permanent_address.split("\n")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(emp.employee_name, emp.bank_ac_no, "IBAN",
                address_lines[0], address_lines[1], cntry,
                salary.amount, account_currency, (unidecode(salary.salary_slip))[-35:], salary.target_date,
                is_salary=1)
            total += salary.amount
        # update total
        self.total = total
        # save
        self.save()

    def on_cancel(self):
        # reset is_proposed
        for purchase_invoice in self.purchase_invoices:
            # un-mark sales invoices as proposed
            invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
            invoice.is_proposed = 0
            invoice.save()        
        for expense_claim in self.expenses:
            # un-mark expense claim as proposed
            invoice = frappe.get_doc("Expense Claim", expense_claim.expense_claim)
            invoice.is_proposed = 0
            invoice.save()   
        for salary_slip in self.salaries:
            # un-mark salary slip as proposed
            invoice = frappe.get_doc("Salary Slip", salary_slip.salary_slip)
            invoice.is_proposed = 0
            invoice.save()
        return
    
    def add_payment(self, receiver_name, iban, payment_type, address_line1, 
        address_line2, country, amount, currency, reference, execution_date, 
        esr_reference=None, esr_participation_number=None, bic=None, is_salary=0):
            # prepare payment date
            if isinstance(execution_date,datetime):
                pay_date = execution_date
            else:
                pay_date = datetime.strptime(execution_date, "%Y-%m-%d")
            # assure that payment date is not in th past
            if pay_date.date() < datetime.now().date():
                pay_date = datetime.now().date()
            # append payment record
            new_payment = self.append('payments', {})
            new_payment.receiver = receiver_name
            new_payment.iban = iban
            new_payment.bic = bic
            new_payment.payment_type = payment_type
            new_payment.receiver_address_line1 = address_line1
            new_payment.receiver_address_line2 = address_line2
            new_payment.receiver_country = country           
            new_payment.amount = amount
            new_payment.currency = currency
            if len(reference) > 140:
                new_payment.reference = "{0}...".format(reference[:136])
            else:
                new_payment.reference = reference
            new_payment.execution_date = pay_date
            new_payment.esr_reference = esr_reference
            new_payment.esr_participation_number = esr_participation_number   
            new_payment.is_salary = is_salary   
            return
    
    def create_payment(self, party_type, party_name, 
                            reference_type, reference_name, date,
                            amount):
        # create new payment entry
        new_payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': "Pay",
            'party_type': party_type,
            'party': party_name,
            'posting_date': date,
            'paid_from': self.intermediate_account,
            'received_amount': amount,
            'paid_amount': amount,
            'reference_no': reference_name,
            'reference_date': date,
            'remarks': "From Payment Proposal {0}".format(self.name),
            'references': [{ 
                'reference_doctype': reference_type,
                'reference_name': reference_name,
                'allocated_amount': amount,
                'due_date': date,
                'total_amount': amount,
                'outstanding_amount': amount
            }]
        })
        inserted_payment_entry = new_payment_entry.insert()
        inserted_payment_entry.submit()
        frappe.db.commit()
        return inserted_payment_entry
        
    @frappe.whitelist()
    def create_bank_file(self):
        data = {}
        data['xml_version'] = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "xml_version")
        data['xml_region'] = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "banking_region")
        data['msgid'] = "MSG-" + time.strftime("%Y%m%d%H%M%S")                # message ID (unique, SWIFT-characters only)
        data['date'] = time.strftime("%Y-%m-%dT%H:%M:%S")                    # creation date and time ( e.g. 2010-02-15T07:30:00 )
        # number of transactions in the file
        transaction_count = 0
        # total amount of all transactions ( e.g. 15850.00 )  (sum of all amounts)
        control_sum = 0.0
        # define company address
        data['company'] = {
            'name': html.escape(self.company)
        }
        company_address = get_primary_address(target_name=self.company, target_type="Company")
        if company_address:
            data['company']['address_line1'] = html.escape(company_address.address_line1)
            data['company']['address_line2'] = "{0} {1}".format(html.escape(company_address.pincode), html.escape(company_address.city))
            data['company']['country_code'] = company_address['country_code']
            # crop lines if required (length limitation)
            data['company']['address_line1'] = data['company']['address_line1'][:35]
            data['company']['address_line2'] = data['company']['address_line2'][:35]
        ### Payment Information (PmtInf, B-Level)
        # payment information records (1 .. 99'999)
        payment_account = frappe.get_doc('Account', self.pay_from_account)
        if not payment_account:
            frappe.throw( _("{0}: no account IBAN found ({1})".format(
                payment.references, self.pay_from_account) ) )
        data['company']['iban'] = "{0}".format(payment_account.iban.replace(" ", ""))
        data['company']['bic'] = payment_account.bic
        data['payments'] = []
        for payment in self.payments:
            payment_content = ""
            payment_record = {
                'id': "PMTINF-{0}-{1}".format(self.name, transaction_count),   # unique (in this file) identification for the payment ( e.g. PMTINF-01, PMTINF-PE-00005 )
                'method': "TRF",             # payment method (TRF or TRA, no impact in Switzerland)
                'batch': "true",             # batch booking (true or false; recommended true)
                'required_execution_date': "{0}".format(payment.execution_date.split(" ")[0]),         # Requested Execution Date (e.g. 2010-02-22, remove time element)
                'debtor': {                    # debitor (technically ignored, but recommended)  
                    'name': html.escape(self.company),
                    'account': "{0}".format(payment_account.iban.replace(" ", "")),
                    'bic': "{0}".format(payment_account.bic)
                },
                'instruction_id': "INSTRID-{0}-{1}".format(self.name, transaction_count),          # instruction identification
                'end_to_end_id': "{0}".format((payment.reference[:33] + '..') if len(payment.reference) > 35 else payment.reference.strip()),   # end-to-end identification (should be used and unique within B-level; payment entry name)
                'currency': payment.currency,
                'amount': round(payment.amount, 2),
                'creditor': {
                    'name': html.escape(payment.receiver),
                    'address_line1': html.escape(payment.receiver_address_line1[:35]),
                    'address_line2': html.escape(payment.receiver_address_line2[:35]),
                    'country_code': frappe.get_value("Country", payment.receiver_country, "code").upper()
                },
                'is_salary': payment.is_salary
            }
            if payment.payment_type == "SEPA":
                # service level code (e.g. SEPA)
                payment_record['service_level'] = "SEPA"
                payment_record['iban'] = payment.iban.replace(" ", "")
                payment_record['reference'] = payment.reference
            elif payment.payment_type == "ESR":
                # Decision whether ESR or QRR
                if 'CH' in payment.esr_participation_number:
                    # It is a QRR
                    payment_record['service_level'] = "QRR"                    # only internal information
                    payment_record['esr_participation_number'] = payment.esr_participation_number.replace(" ", "")                    # handle esr_participation_number as QR-IBAN
                    payment_record['esr_reference'] = payment.esr_reference.replace(" ", "")                    # handle esr_reference as QR-Reference
                else:
                    # proprietary (nothing or CH01 for ESR)            
                    payment_record['local_instrument'] = "CH01"
                    payment_record['service_level'] = "ESR"                    # only internal information
                    payment_record['esr_participation_number'] = payment.esr_participation_number
                    payment_record['esr_reference'] = payment.esr_reference.replace(" ", "")
            else:
                payment_record['service_level'] = "IBAN"
                payment_record['iban'] = payment.iban.replace(" ", "")
                payment_record['reference'] = payment.reference
                payment_record['bic'] = (payment.bic or "").replace(" ", "")
            # once the payment is extracted for payment, submit the record
            transaction_count += 1
            control_sum += round(payment.amount, 2)
            data['payments'].append(payment_record)
        data['transaction_count'] = transaction_count
        data['control_sum'] = control_sum
        
        # render file
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001.html', data)
        return { 'content': content }
    
    def add_creditor_info(self, payment):
        payment_content = ""
        # creditor information
        payment_content += make_line("        <Cdtr>") 
        # name of the creditor/supplier
        payment_content += make_line("          <Nm>" + html.escape(payment.receiver)  + "</Nm>")
        # address of creditor/supplier (should contain at least country and first address line
        payment_content += make_line("          <PstlAdr>")
        # street name
        payment_content += make_line("            <StrtNm>{0}</StrtNm>".format(html.escape(get_street_name(payment.receiver_address_line1))))
        # building number
        payment_content += make_line("            <BldgNb>{0}</BldgNb>".format(html.escape(get_building_number(payment.receiver_address_line1))))
        # postal code
        payment_content += make_line("            <PstCd>{0}</PstCd>".format(html.escape(get_pincode(payment.receiver_address_line2))))
        # town name
        payment_content += make_line("            <TwnNm>{0}</TwnNm>".format(html.escape(get_city(payment.receiver_address_line2))))
        country = frappe.get_doc("Country", payment.receiver_country)
        payment_content += make_line("            <Ctry>" + country.code.upper() + "</Ctry>")
        payment_content += make_line("          </PstlAdr>")
        payment_content += make_line("        </Cdtr>") 
        return payment_content

# this function will create a new payment proposal
@frappe.whitelist()
def create_payment_proposal(date=None, company=None):
    if not date:
        # get planning days
        planning_days = int(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", 'planning_days'))
        date = datetime.now() + timedelta(days=planning_days) 
        if not planning_days:
            frappe.throw( _("Please configure the planning period in ERPNextSwiss Settings.") )
    # check companies (take first created if none specififed)
    if company == None:
        companies = frappe.get_all("Company", filters={}, fields=['name'], order_by='creation')
        company = companies[0]['name']
    # get all suppliers with open purchase invoices
    sql_query = ("""SELECT 
                  `tabPurchase Invoice`.`supplier` AS `supplier`, 
                  `tabPurchase Invoice`.`name` AS `name`,
                  /* if creditor currency = document currency, use outstanding amount, otherwise grand total (in currency) */
                  (IF (`tabPurchase Invoice`.`currency` = `tabAccount`.`account_currency`,
                   `tabPurchase Invoice`.`outstanding_amount`,
                   `tabPurchase Invoice`.`grand_total`
                   )) AS `outstanding_amount`,
                  `tabPurchase Invoice`.`due_date` AS `due_date`, 
                  `tabPurchase Invoice`.`currency` AS `currency`,
                  `tabPurchase Invoice`.`bill_no` AS `external_reference`,
                  (IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, 
                     `tabPurchase Invoice`.`due_date`, 
                     (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY))
                     )) AS `skonto_date`,
                  /* if creditor currency = document currency, use outstanding amount, otherwise grand total (in currency) */
                  (IF (`tabPurchase Invoice`.`currency` = `tabAccount`.`account_currency`,
                    (((100 - IFNULL(`tabPayment Terms Template`.`skonto_percent`, 0))/100) * `tabPurchase Invoice`.`outstanding_amount`),
                    (((100 - IFNULL(`tabPayment Terms Template`.`skonto_percent`, 0))/100) * `tabPurchase Invoice`.`grand_total`)
                    )) AS `skonto_amount`,
                  `tabPurchase Invoice`.`payment_type` AS `payment_type`,
                  `tabPurchase Invoice`.`esr_reference_number` AS `esr_reference`,
                  `tabSupplier`.`esr_participation_number` AS `esr_participation_number`
                FROM `tabPurchase Invoice` 
                LEFT JOIN `tabPayment Terms Template` ON `tabPurchase Invoice`.`payment_terms_template` = `tabPayment Terms Template`.`name`
                LEFT JOIN `tabSupplier` ON `tabPurchase Invoice`.`supplier` = `tabSupplier`.`name`
                LEFT JOIN `tabAccount` ON `tabAccount`.`name` = `tabPurchase Invoice`.`credit_to`
                WHERE `tabPurchase Invoice`.`docstatus` = 1 
                  AND `tabPurchase Invoice`.`outstanding_amount` > 0
                  AND ((`tabPurchase Invoice`.`due_date` <= '{date}') 
                    OR ((IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, `tabPurchase Invoice`.`due_date`, (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)))) <= '{date}'))
                  AND `tabPurchase Invoice`.`is_proposed` = 0
                  AND `tabPurchase Invoice`.`company` = '{company}'
                GROUP BY `tabPurchase Invoice`.`name`;""".format(date=date, company=company))
    purchase_invoices = frappe.db.sql(sql_query, as_dict=True)
    # get all purchase invoices that pending
    total = 0.0
    invoices = []
    for invoice in purchase_invoices:
        reference = invoice.external_reference or invoice.name
        new_invoice = { 
            'supplier': invoice.supplier,
            'purchase_invoice': invoice.name,
            'amount': invoice.outstanding_amount,
            'due_date': invoice.due_date,
            'currency': invoice.currency,
            'skonto_date': invoice.skonto_date,
            'skonto_amount': invoice.skonto_amount,
            'payment_type': invoice.payment_type,
            'esr_reference': invoice.esr_reference,
            'esr_participation_number': invoice.esr_participation_number,
            'external_reference': reference
        }
        total += invoice.skonto_amount
        invoices.append(new_invoice)
    # get all open expense claims
    sql_query = ("""SELECT `name`, 
                  `employee`, 
                  `total_sanctioned_amount` AS `amount`,
                  `payable_account` 
                FROM `tabExpense Claim`
                WHERE `docstatus` = 1 
                  AND `status` = "Unpaid" 
                  AND `is_proposed` = 0
                  AND `company` = '{company}';""".format(company=company))
    expense_claims = frappe.db.sql(sql_query, as_dict=True)          
    # get all purchase invoices that pending
    expenses = []
    for expense in expense_claims:
        new_expense = { 
            'expense_claim': expense.name,
            'employee': expense.employee,
            'amount': expense.amount,
            'payable_account': expense.payable_account
        }
        total += expense.amount
        expenses.append(new_expense)
    # get all open salary slips
    salaries = []
    if cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "enable_salary_payment")) == 1:
        sql_query = ("""SELECT `tabSalary Slip`.`name`, 
                      `tabSalary Slip`.`employee`, 
                      `tabSalary Slip`.`net_pay` AS `amount`,
                      `tabCompany`.`default_payroll_payable_account` AS `payable_account`,
                      `tabSalary Slip`.`posting_date` AS `posting_date`
                    FROM `tabSalary Slip`
                    LEFT JOIN `tabCompany` ON `tabSalary Slip`.`company` = `tabCompany`.`name`
                    WHERE `tabSalary Slip`.`docstatus` = 1 
                      AND `tabSalary Slip`.`is_proposed` = 0
                      AND `tabSalary Slip`.`company` = '{company}';""".format(company=company))
        salary_slips = frappe.db.sql(sql_query, as_dict=True)          
        # append salary slips
        for salary_slip in salary_slips:
            new_salary = { 
                'salary_slip': salary_slip.name,
                'employee': salary_slip.employee,
                'amount': salary_slip.amount,
                'payable_account': salary_slip.payable_account,
                'target_date': salary_slip.posting_date
            }
            total += salary_slip.amount
            salaries.append(new_salary)
    # create new record
    new_record = None
    now = datetime.now()
    date = now + timedelta(days=1)
    new_proposal = frappe.get_doc({
        'doctype': "Payment Proposal",
        'title': "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
        'date': "{year:04d}-{month:02d}-{day:02d}".format(year=date.year, month=date.month, day=date.day),
        'purchase_invoices': invoices,
        'expenses': expenses,
        'salaries': salaries,
        'company': company,
        'total': total
    })
    proposal_record = new_proposal.insert(ignore_permissions=True)      # ignore permissions, as noone has create permission to prevent the new button
    new_record = proposal_record.name
    frappe.db.commit()
    return get_url_to_form("Payment Proposal", new_record)

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"


"""
Allow to release purchase invoices (switch to next revision, before that exists, so it can be cancelled)
"""
@frappe.whitelist()
def release_from_payment_proposal(purchase_invoice):
    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice)
    if pinv.amended_from:
        parts = pinv.name.split("-")
        new_name = "{0}-{1}".format("-".join(parts[:-1]), (cint(parts[-1]) + 1))
    else:
        new_name = "{0}-1".format(pinv.name)
    frappe.db.sql("""UPDATE `tabPayment Proposal Purchase Invoice` 
        SET `purchase_invoice` = "{new_name}" 
        WHERE `purchase_invoice` = "{old_name}";""".format(new_name=new_name, old_name=pinv.name))
    frappe.db.commit()
    return
