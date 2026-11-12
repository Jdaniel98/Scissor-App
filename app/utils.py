import io
import re
import secrets
import string

import qrcode
from qrcode.image.pure import PyPNGImage

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6

# Custom links: 3-32 letters, digits, hyphens or underscores
CUSTOM_CODE_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,32}")

# Paths the app serves itself; a short link with one of these names could never be reached
RESERVED_CODES = {
    "url",
    "urls",
    "shorten",
    "qrcode",
    "download-qrcode",
    "analytics",
    "static",
    "docs",
    "redoc",
    "openapi.json",
}


def generate_short_url() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def is_valid_custom_code(code: str) -> bool:
    return bool(CUSTOM_CODE_PATTERN.fullmatch(code)) and code.lower() not in RESERVED_CODES


def generate_qr_code(data: str) -> bytes:
    """Return a PNG of a QR code that encodes `data`."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(image_factory=PyPNGImage).save(buffer)
    return buffer.getvalue()
