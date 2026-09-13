import frappe
from frappe.model.document import Document


class BankFileHandover(Document):
    def validate(self):
        from erpnextswiss.scripts.bank_file_handover import _controlled_write

        if not _controlled_write.get():
            frappe.throw('Bank file handovers are maintained by the controlled receiver', frappe.PermissionError)

    def on_trash(self):
        frappe.throw('Bank file handover retention requires a separate reviewed operation', frappe.PermissionError)
