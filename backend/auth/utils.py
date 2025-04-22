import pyotp
import qrcode
from io import BytesIO
import base64
import config
from PIL import Image
import pyotp
import time

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
    """
    Verify a TOTP token against a secret, accounting for the time difference
    between the authenticator app (one minute behind) and the server.
    """
    try:
        # Create a TOTP object
        totp = pyotp.TOTP(secret)

        # Calculate time offset: -60 sec (1 minute in the past)
        time_offset = -60

        # Get the adjusted 'client' timestamp (one minute ago)
        adjusted_time = int(time.time()) + time_offset
        adjusted_token = totp.at(adjusted_time)

        # Verify the provided token using the adjusted time
        # This checks if the token matches what the client would see, being 1 minute behind
        return totp.verify(adjusted_token, for_time=adjusted_time)

    except Exception as e:
        print(f"TOTP verification error: {str(e)}")
        return False