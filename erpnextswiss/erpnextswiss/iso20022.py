from datetime import datetime, timezone
import secrets


def create_message_id(now=None, entropy=None):
    """Return a unique pain.001 message ID using only SWIFT-safe characters."""
    timestamp = now or datetime.now(timezone.utc)
    suffix = (entropy or secrets.token_hex(4)).upper()
    message_id = f"MSG-{timestamp.strftime('%Y%m%d%H%M%S%f')}-{suffix}"
    return message_id[:35]


def create_payment_file_name(message_id):
    return f"payments_{message_id}.xml"


def normalize_iban(iban):
    return "".join((iban or "").split()).upper()


def is_qr_iban(iban):
    normalized = normalize_iban(iban)
    if len(normalized) != 21 or not normalized.startswith("CH"):
        return False
    qr_iid = normalized[4:9]
    return qr_iid.isdigit() and 30000 <= int(qr_iid) <= 31999


def resolve_invoice_payment_details(invoice_iban, supplier_iban, supplier_esr, payment_type):
    """Resolve an invoice payment-account override against supplier defaults."""
    invoice_iban = normalize_iban(invoice_iban)
    supplier_iban = normalize_iban(supplier_iban)
    supplier_esr = normalize_iban(supplier_esr)
    iban = invoice_iban or supplier_iban

    if is_qr_iban(iban):
        return "ESR", iban, iban

    method = payment_type or "IBAN"
    participant = None
    if method == "ESR":
        participant = supplier_esr
        # An explicit invoice IBAN takes precedence over a supplier QR-IBAN.
        if invoice_iban and (is_qr_iban(participant) or is_qr_iban(supplier_iban)):
            method = "IBAN"
            participant = None
        elif not participant and is_qr_iban(supplier_iban):
            participant = supplier_iban
    return method, iban, participant


def normalize_qr_reference(reference):
    return "".join((reference or "").split())


def is_valid_qr_reference(reference):
    normalized = normalize_qr_reference(reference)
    if len(normalized) != 27 or not normalized.isdigit():
        return False

    carry = 0
    lookup = (0, 9, 4, 6, 8, 2, 7, 1, 3, 5)
    for digit in normalized[:-1]:
        carry = lookup[(carry + int(digit)) % 10]
    return (10 - carry) % 10 == int(normalized[-1])
