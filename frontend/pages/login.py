import streamlit as st
import requests


def render(api_url, navigate_to):
    st.title("Login")

    # Initialize session state variables if they don't exist
    if 'login_step' not in st.session_state:
        st.session_state.login_step = 1

    # Ensure temp_user_id is initialized but don't reset it
    if 'temp_user_id' not in st.session_state:
        st.session_state.temp_user_id = None

    if st.session_state.login_step == 1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Continue")

            if submitted:
                # Verify username and password
                response = requests.post(
                    f"{api_url}/auth/login",
                    json={
                        "username": username,
                        "password": password
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    # Make sure to preserve the user_id in session state for other scripts
                    st.session_state.temp_user_id = data.get('user_id')

                    if data.get('require_mfa'):
                        st.session_state.login_step = 2
                        st.rerun()
                    else:
                        # No MFA required (unlikely in this app)
                        st.session_state.token = data.get('token')
                        st.session_state.user = data.get('user')
                        navigate_to('home')
                else:
                    try:
                        error_data = response.json()
                        st.error(f"Login failed: {error_data.get('error')}")
                    except:
                        st.error(f"Login failed: {response.text}")

    # Second step: MFA verification
    elif st.session_state.login_step == 2:
        st.subheader("Multi-Factor Authentication")
        st.write("Enter the code from your authenticator app")

        # Display the user ID that will be used
        st.write(f"Processing authentication for user ID: {st.session_state.temp_user_id}")

        with st.form("mfa_form"):
            mfa_token = st.text_input("Authentication Code")
            submitted = st.form_submit_button("Verify")

            if submitted:
                # Verify MFA token
                response = requests.post(
                    f"{api_url}/auth/verify-mfa",
                    json={
                        "user_id": st.session_state.temp_user_id,
                        "mfa_token": mfa_token
                    }
                )
                st.session_state.mfa_token = mfa_token
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data.get('token')

                    # Get user details with the token
                    user_response = requests.get(
                        f"{api_url}/auth/user",
                        headers={"Authorization": f"Bearer {st.session_state.token}"}
                    )

                    if user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                        # Keep temp_user_id in session state even after successful login
                        st.success("Login successful!")
                        navigate_to('home')
                    else:
                        st.error("Failed to retrieve user details")
                else:
                    try:
                        error_data = response.json()
                        st.error(f"MFA verification failed: {error_data.get('error')}")
                    except:
                        st.error(f"MFA verification failed: {response.text}")

    # Add debugging option to see session state (can be removed in production)
    if st.checkbox("Debug: Show session state"):
        st.write("Current session state:")
        st.write(f"login_step: {st.session_state.login_step}")
        st.write(f"temp_user_id: {st.session_state.temp_user_id}")

    st.write("Don't have an account?")
    st.button("Register", on_click=lambda: navigate_to('register'))