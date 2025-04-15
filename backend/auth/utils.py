import pyotp
import qrcode
from io import BytesIO
import base64
import config
from PIL import Image


def generate_mfa_secret():
    """Generate a new MFA secret key"""
    return pyotp.random_base32()


def get_totp_uri(username, secret):
    """Generate the OTP provisioning URI using config settings"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=config.MFA_ISSUER_NAME
    )


def generate_qr_code(totp_uri):
    """Generate QR code image from TOTP URI"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(totp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def verify_totp(secret, token):
    """Verify a TOTP token against a secret"""
    totp = pyotp.TOTP(secret)
    return totp.verify(token)