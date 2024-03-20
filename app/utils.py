import string
import random

import qrcode
from tempfile import NamedTemporaryFile


def generate_short_url():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(6))


def generate_qr_code(url: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=8,
    )
    qr.add_data(url)
    qr.make(fit=True)
    with NamedTemporaryFile(delete=False) as tmp_file:
        # Generate the QR code image
        qr.make_image().save(tmp_file.name)
        return tmp_file.name
