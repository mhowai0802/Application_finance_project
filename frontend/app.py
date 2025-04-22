import sys
import os
import streamlit as st
import logging
import traceback
from contextlib import contextmanager

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import pages and components
from pages import home, login, register, transactions, ai_assistant
from components.sidebar import render_sidebar
from utils.api import test_auth_token  # Assuming this exists in your utils folder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# App configuration
APP_CONFIG = {
    "title": "ExpenseShare HK",
    "icon": "💰",
    "api_url": "http://localhost:5000/api",
    "version": "1.0.0",
    "debug_mode": os.environ.get("DEBUG", "false").lower() == "true"
}

# Custom CSS
CUSTOM_CSS = """
<style>
    /* Hide Streamlit branding and fullscreen button */
    #MainMenu {visibility: hidden;}
    div[data-testid="stSidebarNav"] {display: none;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}

    /* Custom styling */
    .app-header {
        background-color: #f8f9fa;
        padding: 1.5rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border-bottom: 2px solid #e9ecef;
    }

    .app-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
        color: #495057;
    }

    .error-container {
        background-color: #fff5f5;
        border-left: 4px solid #e53e3e;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }

    .footer-text {
        text-align: center;
        color: #6c757d;
        font-size: 0.8rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e9ecef;
    }
</style>
"""


@contextmanager
def error_handling():
    """Context manager for handling errors and providing user feedback"""
    try:
        yield
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())

        if APP_CONFIG["debug_mode"]:
            st.error(f"An error occurred: {str(e)}")
            with st.expander("Error details (Debug Mode)"):
                st.code(traceback.format_exc())
        else:
            st.error("An unexpected error occurred. Please try again or contact support.")

        # Add a refresh button
        if st.button("Refresh Page"):
            st.rerun()


def initialize_session_state():
    """Initialize all required session state variables"""
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = None
    if 'app_notifications' not in st.session_state:
        st.session_state.app_notifications = []


def navigate_to(page):
    """Navigate to a specific page and update session state"""
    # Log page navigation for debugging
    logger.info(f"Navigating from '{st.session_state.page}' to '{page}'")
    st.session_state.page = page


def validate_user_session():
    """Validate the current user session"""
    if not st.session_state.token:
        return False

    try:
        # Test if the token is still valid
        is_valid = test_auth_token(APP_CONFIG["api_url"])
        if not is_valid:
            logger.info("User token is invalid or expired")
            st.session_state.token = None
            st.session_state.user = None
            return False
        return True
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        return False


def render_app_header():
    """Render the application header"""
    if st.session_state.user:
        # Show header with user info for logged-in users
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"<div class='app-header'><h1 class='app-title'>{APP_CONFIG['icon']} {APP_CONFIG['title']}</h1></div>",
                unsafe_allow_html=True)
        # with col2:
        #     st.markdown(
        #         f"<div style='text-align: right; padding-top: 10px;'>Welcome, {st.session_state.user.get('name', 'User')}</div>",
        #         unsafe_allow_html=True)
            # if st.button("Sign Out"):
            #     st.session_state.token = None
            #     st.session_state.user = None
            #     st.session_state.page = 'login'
            #     st.rerun()
    else:
        # Simpler header for non-logged-in users
        st.markdown(
            f"<div class='app-header'><h1 class='app-title'>{APP_CONFIG['icon']} {APP_CONFIG['title']}</h1></div>",
            unsafe_allow_html=True)


def render_footer():
    """Render application footer"""
    st.markdown(f"<div class='footer-text'>© 2025 {APP_CONFIG['title']} | Version {APP_CONFIG['version']}</div>",
                unsafe_allow_html=True)


def process_notifications():
    """Process and display notifications from session state"""
    if st.session_state.app_notifications:
        for notification in st.session_state.app_notifications:
            if notification['type'] == 'error':
                st.error(notification['message'])
            elif notification['type'] == 'success':
                st.success(notification['message'])
            elif notification['type'] == 'info':
                st.info(notification['message'])
            elif notification['type'] == 'warning':
                st.warning(notification['message'])

        # Clear notifications after displaying
        st.session_state.app_notifications = []


def main():
    """Main application entry point"""
    # Configure page settings
    st.set_page_config(
        page_title=APP_CONFIG["title"],
        page_icon=APP_CONFIG["icon"],
        layout="wide",
        initial_sidebar_state="auto"
    )

    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize session state
    initialize_session_state()

    # Process any pending notifications
    process_notifications()

    # Main app logic with error handling
    with error_handling():
        # Render app header
        render_app_header()

        # Check user authentication state
        is_authenticated = validate_user_session() if st.session_state.token else False

        if not is_authenticated:
            # User is not logged in, show auth pages
            if st.session_state.page == 'login':
                login.render(APP_CONFIG["api_url"], navigate_to)
            elif st.session_state.page == 'register':
                register.render(APP_CONFIG["api_url"], navigate_to)
            else:
                # Redirect to login if on unauthorized page
                navigate_to('login')
                st.rerun()
        else:
            # User is logged in, show protected pages
            render_sidebar(navigate_to)

            # Render the selected page
            if st.session_state.page == 'home':
                home.render(APP_CONFIG["api_url"])
            elif st.session_state.page == 'transactions':
                transactions.render(APP_CONFIG["api_url"])
            elif st.session_state.page == 'ai_assistant':
                ai_assistant.render(APP_CONFIG["api_url"])
            else:
                # Fallback to home for unknown pages
                navigate_to('home')
                st.rerun()

        # Render footer
        render_footer()


if __name__ == "__main__":
    main()