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
