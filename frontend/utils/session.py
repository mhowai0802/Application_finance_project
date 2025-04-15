import streamlit as st
import time


def check_session_expired():
    """Check if the current session is expired"""
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
        return False

    # Session timeout after 30 minutes of inactivity
    session_timeout = 30 * 60  # 30 minutes in seconds
    current_time = time.time()

    if current_time - st.session_state.last_activity > session_timeout:
        # Session expired, clear user data
        st.session_state.user = None
        st.session_state.token = None
        st.session_state.page = 'login'
        return True

    # Update last activity time
    st.session_state.last_activity = current_time
    return False


def update_activity():
    """Update the last activity timestamp"""
    st.session_state.last_activity = time.time()


def logout():
    """Log out the current user"""
    st.session_state.user = None
    st.session_state.token = None
    st.session_state.page = 'login'

    # Clear any page-specific state
    keys_to_clear = [key for key in st.session_state.keys() if key not in ['page']]
    for key in keys_to_clear:
        del st.session_state[key]