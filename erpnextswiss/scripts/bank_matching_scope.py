"""Account-bound reads for the existing Bank Wizard matching engine."""

from copy import deepcopy

import frappe


class BankMatchingScope:
    COMPANY_RECORDS = {"Sales Invoice", "Purchase Invoice", "Expense Claim", "Employee", "Payment Entry"}
    OPTIONAL_HR = {"Employee", "Expense Claim"}

    def __init__(self, account):
        frappe.only_for(("Accounts User", "Accounts Manager", "System Manager"))
        if not isinstance(account, str) or not account.strip():
            frappe.throw("Select an authorized bank account", frappe.ValidationError)
        document = frappe.get_doc("Account", account)
        document.check_permission("read")
        if document.account_type != "Bank" or document.disabled or document.is_group or not document.company:
            frappe.throw("An active non-group bank account is required", frappe.ValidationError)
        company = frappe.get_doc("Company", document.company)
        company.check_permission("read")
        self.account = document.name
        self.company = document.company
        self.iban = "".join((document.get("iban") or "").split()).upper()
        self.currency = document.get("account_currency")

    def check_iban(self, iban):
        if not self.iban or "".join(iban.split()).upper() != self.iban:
            frappe.throw("The file IBAN does not match the selected bank account", frappe.ValidationError)

    def records(self, doctype, filters, fields):
        if doctype in self.OPTIONAL_HR and (
                not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read")):
            return []
        if doctype == "Payment Proposal Payment":
            return self._proposal_rows(filters, fields)
        if doctype == "Bank Wizard Pattern":
            # Matching configuration is consumed by Accounts Users too, without
            # granting them permission to edit the Accounts-Manager-only rules.
            return frappe.get_all(doctype, filters=filters, fields=fields)
        if doctype not in self.COMPANY_RECORDS | {"Customer", "Supplier"}:
            frappe.throw("Unsupported bank matching source", frappe.ValidationError)
        scoped = deepcopy(filters)
        if isinstance(scoped, dict):
            scoped = [[key, value[0], value[1]] if isinstance(value, (list, tuple))
                      else [key, "=", value] for key, value in scoped.items()]
        if doctype in self.COMPANY_RECORDS:
            scoped.append(["company", "=", self.company])
        options = {"filters": scoped, "fields": fields, "limit_page_length": 0}
        if doctype == "Payment Entry":
            scoped.append(["docstatus", "!=", 2])
            options["or_filters"] = [["paid_from", "=", self.account], ["paid_to", "=", self.account]]
        return frappe.get_list(doctype, **options)

    def _proposal_rows(self, filters, fields):
        parent = filters.get("parent")
        if not parent or not frappe.has_permission("Payment Proposal", "read"):
            return []
        parents = frappe.get_list("Payment Proposal", filters={"name": parent, "company": self.company},
                                  fields=["name"], limit_page_length=1)
        if not parents:
            return []
        # Child tables have no independent company/permission scope. Resolve the
        # exact authorized parent first; never search child references globally.
        return frappe.get_all("Payment Proposal Payment", filters={**filters, "parent": parents[0]["name"]}, fields=fields)
