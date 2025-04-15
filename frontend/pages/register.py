import streamlit as st
import requests
from PIL import Image
import io
import base64


def render(api_url, navigate_to):
    st.title("Register")

    with st.form("registration_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        phone_number = st.text_input("Phone Number")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")

        submitted = st.form_submit_button("Register")

        if submitted:
            if password != password_confirm:
                st.error("Passwords do not match!")
                return

            # Send registration request
            response = requests.post(
                f"{api_url}/auth/register",
                json={
                    "username": username,
                    "email": email,
                    "phone_number": phone_number,
                    "password": password
                }
            )

            if response.status_code == 201:
                data = response.json()

                # Display QR code for MFA setup
                st.success("Registration successful! Scan this QR code with your authenticator app.")
                qr_code = data.get('qr_code')

                # Convert base64 to image
                img_data = base64.b64decode(qr_code.split(',')[1])
                img = Image.open(io.BytesIO(img_data))
                st.image(img, caption="MFA QR Code")

                # Store the secret for manual entry
                st.info(
                    f"If you cannot scan the QR code, enter this secret manually in your authenticator app: {data.get('mfa_secret')}")

                st.button("Proceed to Login", on_click=lambda: navigate_to('login'))
            else:
                try:
                    error_data = response.json()
                    st.error(f"Registration failed: {error_data.get('error')}")
                except:
                    st.error(f"Registration failed: {response.text}")

    st.write("Already have an account?")
    st.button("Login", on_click=lambda: navigate_to('login'))