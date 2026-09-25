# -*- coding: utf-8 -*-
# Copyright (c) 2018-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
import time
from erpnextswiss.erpnextswiss.common_functions import get_building_number, get_street_name, get_pincode, get_city, get_primary_address, split_address_to_street_and_building
from erpnextswiss.erpnextswiss.iso20022 import (
    create_message_id,
    create_payment_file_name,
    is_qr_iban,
    is_valid_qr_reference,
    resolve_invoice_payment_details,
)
from erpnextswiss.erpnextswiss.xml import validate_xml_against_xsd
import html          # used to escape xml content
from frappe.utils import cint, get_url_to_form, getdate, rounded
from unidecode import unidecode     # used to remove German/French-type special characters from bank identifieres
import os
import re

PAYMENT_REMARKS = "From Payment Proposal {0}"

XML_SCHEMA_FILES = {
    'CH': {
        '03':     "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.03.xsd",
        '05':     "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.05.xsd",
        '03CH02': "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.03.ch.02.xsd",
        '09':     "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.09.xsd",
        '09CH03': "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.09.ch.03.xsd"
    },
    'AT': {
        '03':     "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.03.xsd",
        '05':     "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.05.xsd",
        '03CH02': "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.03.ch.02.xsd",
        '09':     "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.09.xsd",
        '09CH03': "apps/erpnextswiss/erpnextswiss/public/xsd/pain.001.001.09.ch.03.xsd"
    }
}

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
            supplier = frappe.get_doc("Supplier", pinv.supplier)
            payment_type, payment_iban, esr_participation = resolve_invoice_payment_details(
                _doc_get(pinv, "iban"),
                supplier.iban,
                purchase_invoice.esr_participation_number or supplier.esr_participation_number,
                purchase_invoice.payment_type or supplier.default_payment_method,
            )
            purchase_invoice.payment_type = payment_type
            purchase_invoice.esr_participation_number = esr_participation or ""
            # check addresses (mandatory in ISO 20022
            if not pinv.supplier_address:
                frappe.throw( _("Address missing for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
            # check target account info
            if purchase_invoice.payment_type == "ESR":
                if not purchase_invoice.esr_reference or not purchase_invoice.esr_participation_number:
                    frappe.throw( _("ESR: missing transaction information (participant number or reference) in <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
                if is_qr_iban(purchase_invoice.esr_participation_number) and not is_valid_qr_reference(purchase_invoice.esr_reference):
                    frappe.throw( _("QRR: invalid 27-digit QR reference in <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
                if is_qr_iban(purchase_invoice.esr_participation_number):
                    _validate_iban("".join(purchase_invoice.esr_participation_number.split()).upper())
            else:
                if not payment_iban:
                    frappe.throw( _("Missing IBAN for purchase invoice <a href=\"/desk#Form/Purchase Invoice/{0}\">{0}</a>").format(pinv.name) )
                _validate_iban("".join(payment_iban.split()).upper())
        # check expense records
        for expense_claim in self.expenses:
            emp = frappe.get_doc("Employee", expense_claim.employee)
            if not emp.bank_ac_no:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no bank account number.").format(emp.name) )
        return
        
    def on_submit(self):
        if (len(self.purchase_invoices) + len(self.expenses) + len(self.salaries)) == 0:
            frappe.throw( _("No transactions found. You can remove this entry.") )
        # clean payments (to prevent accumulation on re-submit)
        self.payments = []
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
            aggregated_payment_type = None
            # try executing in 90 days (will be reduced by actual due dates)
            exec_date = datetime.combine(getdate(self.date), datetime.min.time()) + timedelta(days=90)
            for purchase_invoice in self.purchase_invoices:
                if purchase_invoice.supplier == supplier:
                    currency = purchase_invoice.currency
                    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    supl = frappe.get_doc("Supplier", supplier)
                    address = pinv.supplier_address
                    references.append(purchase_invoice.external_reference)
                    # find if skonto applies
                    skonto_date = None
                    if purchase_invoice.skonto_date:
                        skonto_date = datetime.combine(
                            getdate(purchase_invoice.skonto_date), datetime.min.time()
                        )
                    due_date = datetime.combine(
                        getdate(purchase_invoice.due_date), datetime.min.time()
                    )
                    if (purchase_invoice.skonto_date) and (skonto_date.date() >= datetime.now().date()):  
                        this_amount = purchase_invoice.skonto_amount    
                        if exec_date.date() > skonto_date.date():
                            exec_date = skonto_date
                    else:
                        this_amount = purchase_invoice.amount
                        if exec_date.date() > due_date.date():
                            exec_date = due_date
                    payment_type, payment_iban, esr_participation = resolve_invoice_payment_details(
                        _doc_get(pinv, "iban"),
                        supl.iban,
                        supl.esr_participation_number,
                        purchase_invoice.payment_type or supl.default_payment_method,
                    )
                    invoice_has_account_override = bool(
                        _doc_get(pinv, "iban") and
                        _normalize_bank_identifier(_doc_get(pinv, "iban")) !=
                        _normalize_bank_identifier(supl.iban)
                    )
                    force_individual = (
                        payment_type == "ESR"
                        or self.individual_payments == 1
                        or invoice_has_account_override
                        or (amount > 0 and aggregated_payment_type != payment_type)
                    )
                    if force_individual:
                        # run as individual payment (not aggregated)
                        addr = frappe.get_doc("Address", address)
                        self.add_payment(
                            receiver_name=supl.supplier_name, 
                            iban=payment_iban,
                            payment_type=payment_type,
                            address_line1=addr.address_line1, 
                            address_line2="{0} {1}".format(addr.pincode, addr.city), 
                            country=addr.country,
                            pincode=addr.pincode,
                            city=addr.city,
                            amount=this_amount, 
                            currency=currency, 
                            reference=purchase_invoice.external_reference, 
                            execution_date=skonto_date or due_date, 
                            esr_reference=purchase_invoice.esr_reference, 
                            esr_participation_number=esr_participation or purchase_invoice.esr_participation_number,
                            bic=supl.bic,
                            receiver_id=supl.name
                        )
                        total += this_amount
                    else:
                        amount += this_amount
                        aggregated_payment_type = payment_type
                    # mark sales invoices as proposed
                    invoice = frappe.get_doc("Purchase Invoice", purchase_invoice.purchase_invoice)
                    invoice.is_proposed = 1
                    invoice.save()
                    # create payment on intermediate
                    if self.use_intermediate == 1:
                        
                        self.create_payment("Supplier", supplier, 
                            "Purchase Invoice", purchase_invoice.purchase_invoice, exec_date,
                            purchase_invoice.amount, self.company)
            # make sure execution date is valid
            if exec_date < datetime.now():
                exec_date = datetime.now()      # + timedelta(days=1)
            # add new payment record
            if amount > 0:
                supl = frappe.get_doc("Supplier", supplier)
                addr = frappe.get_doc("Address", address)
                self.add_payment(
                    receiver_name=supl.supplier_name, 
                    iban=supl.iban, 
                    payment_type=aggregated_payment_type or "IBAN",
                    address_line1=addr.address_line1, 
                    address_line2="{0} {1}".format(addr.pincode, addr.city), 
                    country=addr.country, 
                    pincode=addr.pincode, 
                    city=addr.city,
                    amount=amount, 
                    currency=currency, 
                    reference=" ".join(references), 
                    execution_date=exec_date, 
                    bic=supl.bic, 
                    receiver_id=supl.name
                )
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
                    if cint(self.use_intermediate) == 1:
                        self.create_payment("Employee", employee, 
                            "Expense Claim", expense_claim.expense_claim, exec_date,
                            expense_claim.amount)
            # add new payment record
            emp = frappe.get_doc("Employee", employee)
            if not emp.permanent_address:
                frappe.throw( _("Employee <a href=\"/desk#Form/Employee/{0}\">{0}</a> has no address.").format(emp.name) )
            address_lines = (emp.permanent_address or "").split("\n")
            plz_city = address_lines[1].split(" ")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(
                receiver_name=emp.employee_name, 
                iban=emp.bank_ac_no,
                bic=emp.bic or '',
                payment_type="IBAN",
                address_line1=address_lines[0],
                address_line2=address_lines[1],
                country=cntry,
                pincode=plz_city[0],
                city=plz_city[1],
                amount=amount,
                currency=currency,
                reference=" ".join(references),
                execution_date=self.date
            )
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
            plz_city = address_lines[1].split(" ")
            cntry = frappe.get_value("Company", emp.company, "country")
            self.add_payment(
                receiver_name=emp.employee_name, 
                iban=emp.bank_ac_no,
                bic=emp.bic or '',
                payment_type="IBAN",
                address_line1=address_lines[0],
                address_line2=address_lines[1],
                country=cntry,
                pincode=plz_city[0],
                city=plz_city[1],
                amount=salary.amount,
                currency=account_currency,
                reference=(unidecode(salary.salary_slip))[-35:],
                execution_date=salary.target_date,
                is_salary=1
            )
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
            
        if cint(self.use_intermediate) == 1:
            # cancel payment entries
            payments = frappe.get_all("Payment Entry", 
                filters={'payment_type': "Pay",
                    'paid_from': self.intermediate_account,
                    'remarks': PAYMENT_REMARKS.format(self.name),
                    'docstatus': 1},
                fields=['name']
            )
            for p in payments:
                doc = frappe.get_doc("Payment Entry", p['name'])
                doc.cancel()
                
        return
    
    def add_payment(self, receiver_name, iban, payment_type, address_line1, 
        address_line2, country, pincode, city, amount, currency, reference, execution_date, 
        esr_reference=None, esr_participation_number=None, bic=None, is_salary=0,
        receiver_id=None):
            # prepare payment date
            if isinstance(execution_date,datetime):
                pay_date = execution_date
            else:
                pay_date = datetime.strptime(execution_date, "%Y-%m-%d")
            # assure that payment date is not in th past
            if pay_date.date() < datetime.now().date():
                pay_date = datetime.now().date()
            # append payment record
            new_payment = self.append('payments', {
                'receiver': receiver_name,
                'receiver_id': receiver_id,
                'iban': iban,
                'bic': bic,
                'payment_type': payment_type,
                'receiver_address_line1': address_line1,
                'receiver_address_line2': address_line2,
                'receiver_pincode': pincode,
                'receiver_city': city,
                'receiver_country': country,    
                'amount': amount,
                'currency': currency,
                'reference': "{0}...".format(reference[:136]) if len(reference) > 140 else reference,
                'execution_date': pay_date,
                'esr_reference': esr_reference,
                'esr_participation_number': esr_participation_number,
                'is_salary': is_salary 
            })
            return
    
    def create_payment(self, party_type, party_name, 
                            reference_type, reference_name, date,
                            amount, company):
        intermediate_currency = frappe.get_cached_value("Account", self.intermediate_account, 'account_currency')
        if reference_type == "Purchase Invoice":
            credit_to = frappe.get_value(reference_type, reference_name, "credit_to")
            # if the document is in a foreign currency, calculate to expected value
            if frappe.get_value(reference_type, reference_name, "currency") != intermediate_currency:
                amount = rounded(amount * frappe.get_value(reference_type, reference_name, "conversion_rate"), 2)
        elif reference_type == "Expense Claim":
            credit_to = frappe.get_value(reference_type, reference_name, "payable_account")
        elif reference_type == "Expense Claim":
            credit_to = frappe.get_value("Company", 
                frappe.get_value(reference_type, reference_name, "company"), "default_payroll_payable_account")
        # create new payment entry
        new_payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'company': company, 
            'payment_type': "Pay",
            'party_type': party_type,
            'party': party_name,
            'posting_date': date,
            'paid_from': self.intermediate_account,
            'paid_to': credit_to,
            'received_amount': amount,
            'paid_amount': amount,
            'reference_no': reference_name,
            'reference_date': date,
            'remarks': PAYMENT_REMARKS.format(self.name),
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
        
    @frappe.whitelist(methods=["POST"])
    def create_bank_file(self):
        self.check_permission("write")
        data = {}
        settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
        data['xml_version'] = settings.get("xml_version")
        data['xml_region'] = settings.get("banking_region")
        data['msgid'] = create_message_id()                                  # message ID (unique, SWIFT-characters only)
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
            data['company']['pincode'] = html.escape(company_address.pincode)
            data['company']['city'] = html.escape(company_address.city)
            # crop lines if required (length limitation)
            data['company']['address_line1'] = data['company']['address_line1'][:35]
            data['company']['address_line2'] = data['company']['address_line2'][:35]
            data['company']['street'] = html.escape(get_street_name(data['company']['address_line1'])[:35])
            data['company']['building'] = html.escape(get_building_number(data['company']['address_line1'])[:5])
            data['company']['pincode'] = data['company']['pincode'][:16]
            data['company']['city'] = data['company']['city'][:35]
        ### Payment Information (PmtInf, B-Level)
        # payment information records (1 .. 99'999)
        payment_account = frappe.get_doc('Account', self.pay_from_account)
        if not payment_account.iban or not payment_account.bic:
            frappe.throw( _("Account {0} is missing IBAN and/or BIC".format(
                self.pay_from_account) ) )
        data['company']['iban'] = "{0}".format(payment_account.iban.replace(" ", ""))
        data['company']['bic'] = "{0}".format(payment_account.bic.replace(" ", ""))
        data['payments'] = []
        for payment in self.payments:
            payment_content = ""
            payment_type = payment.payment_type
            qr_iban = payment.esr_participation_number or payment.iban
            if is_qr_iban(qr_iban):
                if not is_valid_qr_reference(payment.esr_reference):
                    frappe.throw(
                        _("Payment {0}: a QR-IBAN requires a valid 27-digit QR reference.").format(
                            payment.idx
                        )
                    )
                payment_type = "ESR"
            execution_date = payment.execution_date
            if isinstance(execution_date, datetime):
                execution_date = execution_date.date().isoformat()
            elif hasattr(execution_date, "isoformat"):
                execution_date = execution_date.isoformat()
            else:
                execution_date = str(execution_date).split(" ")[0]
            payment_record = {
                'id': "PMTINF-{0}-{1}".format(self.name, transaction_count),   # unique (in this file) identification for the payment ( e.g. PMTINF-01, PMTINF-PE-00005 )
                'method': "TRF",             # payment method (TRF or TRA, no impact in Switzerland)
                'batch': "true",             # batch booking (true or false; recommended true)
                'required_execution_date': execution_date,         # Requested Execution Date (e.g. 2010-02-22, remove time element)
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
                    'street': html.escape(get_street_name(payment.receiver_address_line1)[:35]),
                    'building': html.escape(get_building_number(payment.receiver_address_line1)[:5]),
                    'country_code': frappe.get_value("Country", payment.receiver_country, "code").upper(),
                    'pincode': html.escape((payment.receiver_pincode or "")[:16]),
                    'city': html.escape((payment.receiver_city or "")[:35])
                },
                'is_salary': payment.is_salary
            }
            if payment_type == "SEPA":
                # service level code (e.g. SEPA)
                payment_record['service_level'] = "SEPA"
                payment_record['iban'] = payment.iban.replace(" ", "")
                payment_record['reference'] = payment.reference
            elif payment_type == "ESR":
                # Decision whether ESR or QRR
                if is_qr_iban(qr_iban):
                    # It is a QRR
                    payment_record['service_level'] = "QRR"                    # only internal information
                    payment_record['esr_participation_number'] = qr_iban.replace(" ", "")                    # handle esr_participation_number as QR-IBAN
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
        single_payment = cint(self.get("single_payment"))
        if data['xml_version'] == "09" and not single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001-001-09.html', data)
        elif data['xml_version'] == "09" and single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001-001-09_single_payment.html', data)
        elif single_payment:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001_single_payment.html', data)
        else:
            content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/pain-001.html', data)
        
        # apply unidecode if enabled
        if cint(settings.get("use_unidecode")) == 1:
            content = unidecode(content)
        
        # validate xml
        if cint(settings.get("validate_xml")) == 1:
            xml_schema = os.path.join(frappe.utils.get_bench_path(), XML_SCHEMA_FILES[settings.get("banking_region")][settings.get("xml_version")])
            validated, errors = validate_xml_against_xsd(content, xml_schema)
            if not validated:
                frappe.log_error("{0}\n\n{1}".format(errors, content), "XML validation failed (pain.001)")
                frappe.throw("Validation error: {0}".format(errors))
        
        return {
            'content': content,
            'file_name': create_payment_file_name(data['msgid']),
            'message_id': data['msgid']
        }
    
    def create_wise_file(self):
        data = {
            'payments': []
        }
        source_currency = frappe.get_cached_value("Account", self.pay_from_account, "account_currency")
        for payment in self.payments:
            data['payments'].append({
                'recipient': payment.receiver,
                'recipient_mail': "",
                'reference': payment.reference,
                'amount': rounded(payment.amount, 2),
                'source_currency': source_currency,
                'target_currency': payment.currency,
                'iban': payment.iban.replace(" ", "")
            })

        # render file
        content = frappe.render_template('erpnextswiss/erpnextswiss/doctype/payment_proposal/transferwise_payments.html', data)
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
        
    @frappe.whitelist()
    def has_active_ebics_connection(self):
        statements = frappe.db.sql("""
            SELECT `ebics_connection` 
            FROM `tabebics Statement`
            WHERE `account` = "{account}"
            ORDER BY `creation` DESC;
            """.format(account=self.pay_from_account), as_dict=True)
        if len(statements) > 0:
            connections = frappe.db.sql("""
            SELECT `activated`, `name` 
            FROM `tabebics Connection`
            WHERE `name` = "{conn}";
            """.format(conn=statements[0]['ebics_connection']), as_dict=True)
            if len(connections) > 0:
                return connections[0]['name']
        return 0
        
def _truthy(value, default=False):
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "ja")
    return bool(value)


def _normalize_bank_identifier(value):
    if value is None:
        return None
    return re.sub(r"[^0-9A-Za-z]", "", str(value)).upper()


def _optional_float(value, fieldname):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        frappe.throw(_("{0} must be a number.").format(fieldname))


def _optional_int(value, fieldname):
    if value is None or value == "":
        return None
    try:
        return cint(value)
    except Exception:
        frappe.throw(_("{0} must be a whole number.").format(fieldname))


def _assert_expected_total(actual, expected_total):
    expected = _optional_float(expected_total, "expected_total")
    if expected is not None and round(abs(float(actual or 0) - expected), 2) > 0:
        frappe.throw(
            _("Expected total {0} does not match calculated total {1}.").format(
                expected, rounded(float(actual or 0), 2)
            )
        )


def _assert_expected_count(actual, expected_count, fieldname):
    expected = _optional_int(expected_count, fieldname)
    if expected is not None and cint(actual) != expected:
        frappe.throw(
            _("Expected {0} {1} does not match calculated value {2}.").format(
                fieldname, expected, actual
            )
        )


def _require_confirmed(confirm, action):
    if not _truthy(confirm):
        frappe.throw(_("Confirmation is required before {0}.").format(action))


def _get_default_company():
    companies = frappe.get_all("Company", filters={}, fields=["name"], order_by="creation")
    if not companies:
        frappe.throw(_("Please create a company first."))
    return companies[0]["name"]


def _get_payment_proposal_cutoff(date):
    if date:
        return getdate(date)

    planning_days = cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "planning_days"))
    if not planning_days:
        frappe.throw(_("Please configure the planning period in ERPNextSwiss Settings."))
    return getdate(datetime.now() + timedelta(days=planning_days))


def _include_salary_payments(include_salary_slips):
    if include_salary_slips is None:
        return cint(frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "enable_salary_payment")) == 1
    return _truthy(include_salary_slips)


def _collect_payment_proposal_rows(date, company, currency=None, include_expense_claims=True, include_salary_slips=None):
    date = _get_payment_proposal_cutoff(date)
    company = company or _get_default_company()

    purchase_invoices = frappe.db.sql(
        """SELECT
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
              `tabPurchase Invoice`.`iban` AS `invoice_iban`,
              `tabPurchase Invoice`.`esr_reference_number` AS `esr_reference`,
              `tabSupplier`.`esr_participation_number` AS `esr_participation_number`,
              `tabSupplier`.`iban` AS `supplier_iban`,
              `tabSupplier`.`default_payment_method` AS `supplier_default_payment_method`
            FROM `tabPurchase Invoice`
            LEFT JOIN `tabPayment Terms Template` ON `tabPurchase Invoice`.`payment_terms_template` = `tabPayment Terms Template`.`name`
            LEFT JOIN `tabSupplier` ON `tabPurchase Invoice`.`supplier` = `tabSupplier`.`name`
            LEFT JOIN `tabAccount` ON `tabAccount`.`name` = `tabPurchase Invoice`.`credit_to`
            WHERE `tabPurchase Invoice`.`docstatus` = 1
              AND `tabPurchase Invoice`.`outstanding_amount` > 0
              AND ((`tabPurchase Invoice`.`due_date` <= %(date)s)
                OR ((IF (IFNULL(`tabPayment Terms Template`.`skonto_days`, 0) = 0, `tabPurchase Invoice`.`due_date`, (DATE_ADD(`tabPurchase Invoice`.`posting_date`, INTERVAL `tabPayment Terms Template`.`skonto_days` DAY)))) <= %(date)s))
              AND `tabPurchase Invoice`.`is_proposed` = 0
              AND `tabPurchase Invoice`.`company` = %(company)s
            GROUP BY `tabPurchase Invoice`.`name`;""",
        {"date": date, "company": company},
        as_dict=True,
    )

    total = 0.0
    invoices = []
    for invoice in purchase_invoices:
        if currency and invoice.currency != currency:
            continue
        reference = invoice.external_reference or invoice.name
        payment_type, payment_iban, esr_participation = resolve_invoice_payment_details(
            invoice.invoice_iban,
            invoice.supplier_iban,
            invoice.esr_participation_number,
            invoice.payment_type or invoice.supplier_default_payment_method,
        )
        skonto_amount = float(invoice.skonto_amount or 0)
        invoices.append({
            "supplier": invoice.supplier,
            "purchase_invoice": invoice.name,
            "amount": invoice.outstanding_amount,
            "due_date": invoice.due_date,
            "currency": invoice.currency,
            "skonto_date": invoice.skonto_date,
            "skonto_amount": invoice.skonto_amount,
            "payment_type": payment_type,
            "esr_reference": invoice.esr_reference,
            "esr_participation_number": esr_participation or invoice.esr_participation_number,
            "external_reference": unidecode(reference),
        })
        total += skonto_amount

    expenses = []
    if _truthy(include_expense_claims, default=True) and (
        not currency or currency == frappe.get_cached_value("Company", company, "default_currency")
    ):
        expense_claims = frappe.db.sql(
            """SELECT `name`,
                  `employee`,
                  `total_sanctioned_amount` AS `amount`,
                  `payable_account`
                FROM `tabExpense Claim`
                WHERE `docstatus` = 1
                  AND `status` = "Unpaid"
                  AND `is_proposed` = 0
                  AND `company` = %(company)s;""",
            {"company": company},
            as_dict=True,
        )
        for expense in expense_claims:
            amount = float(expense.amount or 0)
            expenses.append({
                "expense_claim": expense.name,
                "employee": expense.employee,
                "amount": expense.amount,
                "payable_account": expense.payable_account,
            })
            total += amount

    salaries = []
    if _include_salary_payments(include_salary_slips) and (
        not currency or currency == frappe.get_cached_value("Company", company, "default_currency")
    ):
        salary_slips = frappe.db.sql(
            """SELECT `tabSalary Slip`.`name`,
                  `tabSalary Slip`.`employee`,
                  `tabSalary Slip`.`net_pay` AS `amount`,
                  `tabCompany`.`default_payroll_payable_account` AS `payable_account`,
                  `tabSalary Slip`.`posting_date` AS `posting_date`
                FROM `tabSalary Slip`
                LEFT JOIN `tabCompany` ON `tabSalary Slip`.`company` = `tabCompany`.`name`
                WHERE `tabSalary Slip`.`docstatus` = 1
                  AND `tabSalary Slip`.`is_proposed` = 0
                  AND `tabSalary Slip`.`net_pay` > 0
                  AND `tabSalary Slip`.`company` = %(company)s;""",
            {"company": company},
            as_dict=True,
        )
        for salary_slip in salary_slips:
            amount = float(salary_slip.amount or 0)
            salaries.append({
                "salary_slip": salary_slip.name,
                "employee": salary_slip.employee,
                "amount": salary_slip.amount,
                "payable_account": salary_slip.payable_account,
                "target_date": salary_slip.posting_date,
            })
            total += amount

    return {
        "date": date,
        "company": company,
        "currency": currency,
        "purchase_invoices": invoices,
        "expenses": expenses,
        "salaries": salaries,
        "total": total,
    }


def _assert_payment_proposal_expectations(rows, expected_total=None, expected_purchase_invoice_count=None,
                                          expected_expense_count=None, expected_salary_count=None):
    _assert_expected_total(rows["total"], expected_total)
    _assert_expected_count(
        len(rows["purchase_invoices"]),
        expected_purchase_invoice_count,
        "expected_purchase_invoice_count",
    )
    _assert_expected_count(len(rows["expenses"]), expected_expense_count, "expected_expense_count")
    _assert_expected_count(len(rows["salaries"]), expected_salary_count, "expected_salary_count")


def _create_payment_proposal_record(date=None, company=None, currency=None, title=None, payment_date=None,
                                    pay_from_account=None, include_expense_claims=True,
                                    include_salary_slips=None, expected_total=None,
                                    expected_purchase_invoice_count=None, expected_expense_count=None,
                                    expected_salary_count=None, commit=True):
    rows = _collect_payment_proposal_rows(
        date=date,
        company=company,
        currency=currency,
        include_expense_claims=include_expense_claims,
        include_salary_slips=include_salary_slips,
    )
    _assert_payment_proposal_expectations(
        rows,
        expected_total=expected_total,
        expected_purchase_invoice_count=expected_purchase_invoice_count,
        expected_expense_count=expected_expense_count,
        expected_salary_count=expected_salary_count,
    )

    if not rows["purchase_invoices"] and not rows["expenses"] and not rows["salaries"]:
        return None

    now = datetime.now()
    payment_date = getdate(payment_date) if payment_date else getdate(now + timedelta(days=1))
    proposal_data = {
        "doctype": "Payment Proposal",
        "title": title or "{year:04d}-{month:02d}-{day:02d}".format(year=now.year, month=now.month, day=now.day),
        "date": "{year:04d}-{month:02d}-{day:02d}".format(
            year=payment_date.year,
            month=payment_date.month,
            day=payment_date.day,
        ),
        "purchase_invoices": rows["purchase_invoices"],
        "expenses": rows["expenses"],
        "salaries": rows["salaries"],
        "company": rows["company"],
        "total": rows["total"],
    }
    if pay_from_account:
        proposal_data["pay_from_account"] = pay_from_account

    new_proposal = frappe.get_doc(proposal_data)
    # The ordinary New button is intentionally disabled for this DocType; controlled helpers create via whitelisted flows.
    proposal_record = new_proposal.insert(ignore_permissions=True)
    if commit:
        frappe.db.commit()
    return proposal_record


def _row_value(row, key):
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _summarize_child_rows(rows, fields):
    return [
        {field: _row_value(row, field) for field in fields}
        for row in (rows or [])
    ]


def _payment_proposal_summary(doc):
    return {
        "success": True,
        "name": doc.name,
        "url": get_url_to_form("Payment Proposal", doc.name),
        "docstatus": doc.docstatus,
        "title": doc.title,
        "date": doc.date,
        "company": doc.company,
        "pay_from_account": doc.pay_from_account,
        "total": float(doc.total or 0),
        "purchase_invoice_count": len(doc.purchase_invoices or []),
        "expense_count": len(doc.expenses or []),
        "salary_count": len(doc.salaries or []),
        "payment_count": len(doc.payments or []),
        "purchase_invoices": _summarize_child_rows(
            doc.purchase_invoices,
            ("supplier", "purchase_invoice", "amount", "currency", "due_date", "payment_type", "external_reference"),
        ),
        "expenses": _summarize_child_rows(doc.expenses, ("employee", "expense_claim", "amount", "payable_account")),
        "salaries": _summarize_child_rows(doc.salaries, ("employee", "salary_slip", "amount", "payable_account")),
        "payments": _summarize_child_rows(
            doc.payments,
            ("receiver_name", "iban", "amount", "currency", "reference", "payment_type", "party_reference"),
        ),
    }


# this function will create a new payment proposal for the desk list view
@frappe.whitelist(methods=["POST"])
def create_payment_proposal(date=None, company=None, currency=None):
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    proposal_record = _create_payment_proposal_record(
        date=date,
        company=company,
        currency=currency,
        include_expense_claims=True,
        include_salary_slips=None,
    )
    if not proposal_record:
        return None
    return get_url_to_form("Payment Proposal", proposal_record.name)


@frappe.whitelist(methods=["POST"])
def create_payment_proposal_for_mcp(date=None, company=None, currency=None, pay_from_account=None, title=None,
                                    include_expense_claims=1, include_salary_slips=0, submit=0,
                                    expected_total=None, expected_purchase_invoice_count=None,
                                    expected_expense_count=None, expected_salary_count=None,
                                    payment_date=None, confirm=0, reason=None):
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    submit_now = _truthy(submit)
    if submit_now:
        _require_confirmed(confirm, "submitting a payment proposal")
        if not pay_from_account:
            frappe.throw(_("pay_from_account is required when submit is enabled."))

    proposal_record = _create_payment_proposal_record(
        date=date,
        company=company,
        currency=currency,
        title=title,
        payment_date=payment_date,
        pay_from_account=pay_from_account,
        include_expense_claims=include_expense_claims,
        include_salary_slips=include_salary_slips,
        expected_total=expected_total,
        expected_purchase_invoice_count=expected_purchase_invoice_count,
        expected_expense_count=expected_expense_count,
        expected_salary_count=expected_salary_count,
        commit=not submit_now,
    )
    if not proposal_record:
        frappe.throw(_("No suitable invoices, expense claims or salary slips found."))

    if submit_now:
        proposal_record.submit()
        frappe.db.commit()
        proposal_record = frappe.get_doc("Payment Proposal", proposal_record.name)

    return _payment_proposal_summary(proposal_record)


@frappe.whitelist(methods=["POST"])
def cancel_payment_proposal_for_mcp(payment_proposal=None, name=None, expected_total=None,
                                    expected_payment_count=None, confirm=0, reason=None):
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    _require_confirmed(confirm, "cancelling a payment proposal")
    proposal_name = payment_proposal or name
    if not proposal_name:
        frappe.throw(_("payment_proposal is required."))

    doc = frappe.get_doc("Payment Proposal", proposal_name)
    doc.check_permission("write")
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted payment proposals can be cancelled."))
    _assert_expected_total(doc.total, expected_total)
    _assert_expected_count(len(doc.payments or []), expected_payment_count, "expected_payment_count")

    doc.cancel()
    frappe.db.commit()
    doc = frappe.get_doc("Payment Proposal", proposal_name)
    return _payment_proposal_summary(doc)


@frappe.whitelist(methods=["POST"])
def create_payment_proposal_bank_file_for_mcp(payment_proposal=None, name=None, expected_total=None,
                                              expected_payment_count=None, confirm=0, reason=None):
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    _require_confirmed(confirm, "creating a payment proposal bank file")
    proposal_name = payment_proposal or name
    if not proposal_name:
        frappe.throw(_("payment_proposal is required."))

    doc = frappe.get_doc("Payment Proposal", proposal_name)
    doc.check_permission("write")
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted payment proposals can be exported."))
    _assert_expected_total(doc.total, expected_total)
    _assert_expected_count(len(doc.payments or []), expected_payment_count, "expected_payment_count")

    result = doc.create_bank_file()
    return {
        "success": True,
        "name": doc.name,
        "total": float(doc.total or 0),
        "payment_count": len(doc.payments or []),
        "file_name": result.get("file_name"),
        "message_id": result.get("message_id"),
        "content": result.get("content"),
    }


def _validate_iban(iban):
    if not iban:
        return
    if not re.match(r"^[A-Z]{2}[0-9A-Z]{13,32}$", iban):
        frappe.throw(_("Invalid IBAN format."))
    rearranged = "{0}{1}".format(iban[4:], iban[:4])
    converted = "".join(str(int(char, 36)) if char.isalpha() else char for char in rearranged)
    checksum = 0
    for char in converted:
        checksum = (checksum * 10 + cint(char)) % 97
    if checksum != 1:
        frappe.throw(_("Invalid IBAN checksum."))


def _validate_bic(bic):
    if bic and not re.match(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$", bic):
        frappe.throw(_("Invalid BIC format."))


def _doc_get(doc, fieldname):
    try:
        return doc.get(fieldname)
    except Exception:
        return getattr(doc, fieldname, None)


def _set_supplier_field(doc, fieldname, value):
    if not doc.meta.has_field(fieldname):
        frappe.throw(_("Supplier field {0} is not available.").format(fieldname))
    doc.set(fieldname, value)


@frappe.whitelist(methods=["POST"])
def set_supplier_payment_details_for_mcp(supplier=None, default_payment_method="IBAN", iban=None, bic=None,
                                         esr_participation_number=None, clear_esr_participation_number=0,
                                         confirm=0, reason=None):
    frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
    _require_confirmed(confirm, "updating supplier payment details")
    if not supplier:
        frappe.throw(_("supplier is required."))

    supplier_doc = frappe.get_doc("Supplier", supplier)
    supplier_doc.check_permission("write")

    default_payment_method = (default_payment_method or "").strip().upper()
    if default_payment_method not in ("IBAN", "ESR", "SEPA"):
        frappe.throw(_("Unsupported default payment method {0}.").format(default_payment_method))

    normalized_iban = _normalize_bank_identifier(iban) if iban is not None else _normalize_bank_identifier(_doc_get(supplier_doc, "iban"))
    normalized_bic = _normalize_bank_identifier(bic) if bic is not None else _normalize_bank_identifier(_doc_get(supplier_doc, "bic"))
    normalized_esr = (
        _normalize_bank_identifier(esr_participation_number)
        if esr_participation_number is not None
        else _normalize_bank_identifier(_doc_get(supplier_doc, "esr_participation_number"))
    )

    if default_payment_method in ("IBAN", "SEPA") and not normalized_iban:
        frappe.throw(_("IBAN is required for payment method {0}.").format(default_payment_method))
    if default_payment_method == "ESR" and not normalized_esr:
        frappe.throw(_("ESR participation number is required for payment method ESR."))

    _validate_iban(normalized_iban)
    _validate_bic(normalized_bic)
    _set_supplier_field(supplier_doc, "default_payment_method", default_payment_method)
    if iban is not None:
        _set_supplier_field(supplier_doc, "iban", normalized_iban)
    if bic is not None:
        _set_supplier_field(supplier_doc, "bic", normalized_bic)
    if _truthy(clear_esr_participation_number):
        _set_supplier_field(supplier_doc, "esr_participation_number", "")
        normalized_esr = ""
    elif esr_participation_number is not None:
        _set_supplier_field(supplier_doc, "esr_participation_number", normalized_esr)

    supplier_doc.save()
    frappe.db.commit()
    return {
        "success": True,
        "supplier": supplier_doc.name,
        "default_payment_method": _doc_get(supplier_doc, "default_payment_method"),
        "iban": _doc_get(supplier_doc, "iban"),
        "bic": _doc_get(supplier_doc, "bic"),
        "esr_participation_number": _doc_get(supplier_doc, "esr_participation_number"),
    }

# adds Windows-compatible line endings (to make the xml look nice)    
def make_line(line):
    return line + "\r\n"


"""
Allow to release purchase invoices (switch to next revision, before that exists, so it can be cancelled)
"""
@frappe.whitelist(methods=["POST"])
def release_from_payment_proposal(purchase_invoice):
    pinv = frappe.get_doc("Purchase Invoice", purchase_invoice)
    pinv.check_permission("write")
    if pinv.amended_from:
        parts = pinv.name.split("-")
        new_name = "{0}-{1}".format("-".join(parts[:-1]), (cint(parts[-1]) + 1))
    else:
        new_name = "{0}-1".format(pinv.name)
    frappe.db.sql(
        """UPDATE `tabPayment Proposal Purchase Invoice`
        SET `purchase_invoice` = %(new_name)s
        WHERE `purchase_invoice` = %(old_name)s""",
        {"new_name": new_name, "old_name": pinv.name},
    )
    return
