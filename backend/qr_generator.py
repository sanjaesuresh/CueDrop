"""Session QR code generation."""

from __future__ import annotations

import io

import qrcode
from qrcode.image.pil import PilImage


def generate(session_id: str, base_url: str = "http://localhost:8000") -> bytes:
    """Generate a QR code PNG encoding the guest URL for a session."""
    url = f"{base_url}/guest/{session_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img: PilImage = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
