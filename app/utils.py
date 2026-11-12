import io

import qrcode
from qrcode.image.pure import PyPNGImage
from qrcode.image.svg import SvgPathImage


def _qr(data: str) -> qrcode.QRCode:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr


def generate_qr_code(data: str) -> bytes:
    """Return a PNG of a QR code that encodes `data`."""
    buffer = io.BytesIO()
    _qr(data).make_image(image_factory=PyPNGImage).save(buffer)
    return buffer.getvalue()


def generate_qr_svg(data: str) -> bytes:
    """Return an SVG of a QR code that encodes `data`; it scales to any size."""
    buffer = io.BytesIO()
    _qr(data).make_image(image_factory=SvgPathImage).save(buffer)
    return buffer.getvalue()
