"""Durable EBICS receipt; the bank acknowledgement is separate from booking."""

from frappe.model.document import Document


class EBICSDownload(Document):
    pass
