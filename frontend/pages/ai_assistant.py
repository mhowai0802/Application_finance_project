import streamlit as st
import requests
import json
import logging
from pages.transactions import render_mfa_verification
from utils.api import api_get, api_post, get_endpoint_url, test_auth_token

# Configure logging
logger = logging.getLogger("ai_assistant")
logging.basicConfig(level=logging.INFO)


def initialize_session_state():
    """Initialize all session state variables if they don't exist"""
    if 'transactions_view' not in st.session_state:
        st.session_state.transactions_view = 'new'
    if 'ai_chat_history' not in st.session_state:
        st.session_state.ai_chat_history = []
    if 'active_function' not in st.session_state:
        st.session_state.active_function = "regular"
    if 'pending_transaction_id' not in st.session_state:
        st.session_state.pending_transaction_id = ""
    if 'transaction_details' not in st.session_state:
        st.session_state.transaction_details = {}


def display_chat_history():
    """Display the chat history with better styling"""
    for message in st.session_state.ai_chat_history:
        if message['role'] == 'user':
            st.markdown(
                f"""<div style='background-color: #e6f7ff; padding: 10px; 
                border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #1E90FF;'>
                <strong>You:</strong> {message['content']}</div>""",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"""<div style='background-color: #f0f0f0; padding: 10px; 
                border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #32CD32;'>
                <strong>AI:</strong> {message['content']}</div>""",
                unsafe_allow_html=True)


def validate_token(api_url):
    """Validate the authentication token and return status"""
    if 'token' not in st.session_state or not st.session_state.token:
        st.error("You are not logged in. Please log in to continue.")
        return False

    token_valid = test_auth_token(api_url)
    if not token_valid:
        st.warning("Your session has expired. Please log in again.")
        return False

    return True


def ask_ai(question, api_url):
    """Send a question to the regular AI assistant"""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        with st.spinner("AI is thinking..."):
            response = requests.post(
                f"{api_url}/ai/chat",
                headers=headers,
                json={"message": question},
                timeout=30
            )

        if response.status_code == 200:
            return response.json().get('response', "No response received")
        else:
            logger.error(f"AI request failed with status {response.status_code}: {response.text}")
            return f"Error: Unable to get a response (Status: {response.status_code})"
    except requests.exceptions.Timeout:
        return "Error: The request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "Error: Unable to connect to the server. Please check your internet connection."
    except Exception as e:
        logger.exception("Error in ask_ai function")
        return f"An unexpected error occurred: {str(e)}"


def call_financial_tool_api(query, api_url):
    """Process a query using the financial analysis tool"""
    if not validate_token(api_url):
        return "Please log in to use the financial tool."
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        user_id = st.session_state.get('temp_user_id', 'unknown')

        enriched_query = f"{query} (user id: {user_id})"

        with st.spinner("Processing financial request..."):
            response = requests.post(
                f"{api_url}/ai/financial_tool",
                headers=headers,
                json={"query": enriched_query},
                timeout=45
            )

        if response.status_code != 200:
            logger.error(f"Financial tool request failed with status {response.status_code}: {response.text}")
            return f"Error: The financial tool returned an error (Status: {response.status_code})"

        transaction_data = response.json().get('answer', {})
        st.session_state.transaction_details = transaction_data

        # Initiate the transaction
        transaction_url = get_endpoint_url(api_url, "transactions", "initiate")
        transaction_response = requests.post(
            transaction_url,
            json=transaction_data,
            headers={
                "Authorization": f"Bearer {st.session_state.token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if transaction_response.status_code not in [200, 201]:
            logger.error(
                f"Transaction initiation failed: {transaction_response.status_code}: {transaction_response.text}")
            return f"Error initiating transaction: {transaction_response.status_code}"

        # Store transaction ID and update view
        response_data = transaction_response.json()
        transaction_id = response_data.get('transaction_id', 'unknown')
        st.session_state.pending_transaction_id = transaction_id
        st.session_state.transactions_view = 'mfa'

        return f"Transaction details processed. Transaction ID: {transaction_id}."

    except requests.exceptions.Timeout:
        return "Error: The request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "Error: Unable to connect to the server. Please check your internet connection."
    except Exception as e:
        logger.exception("Error in financial tool function")
        return f"An unexpected error occurred: {str(e)}"


def render(api_url):
    """Main render function for the AI Financial Assistant"""
    st.title("AI Financial Assistant")

    # Initialize session state
    initialize_session_state()

    # Handle MFA verification view if active
    if st.session_state.transactions_view == 'mfa':
        token_valid = validate_token(api_url)
        render_mfa_verification(api_url, token_valid, st.session_state.pending_transaction_id)

        # Add a back button
        if st.button("← Back to Assistant"):
            st.session_state.transactions_view = 'new'
            st.rerun()

        return

    # Main assistant interface
    with st.sidebar:
        st.header("Mode Selection")
        st.radio(
            "Select assistant mode:",
            ["Regular AI", "Financial Tool"],
            key="mode_selection",
            index=0 if st.session_state.active_function == "regular" else 1,
            on_change=lambda: setattr(st.session_state, 'active_function',
                                      "regular" if st.session_state.mode_selection == "Regular AI" else "financial")
        )

        if st.button("Clear Chat History"):
            st.session_state.ai_chat_history = []
            st.rerun()

    # Show current mode
    mode_color = "#1E90FF" if st.session_state.active_function == "regular" else "#32CD32"
    st.markdown(
        f"""<div style='padding: 5px 15px; background-color: {mode_color}25; 
        border-radius: 5px; display: inline-block; margin-bottom: 20px;'>
        <strong>Current mode:</strong> {st.session_state.active_function.title()}</div>""",
        unsafe_allow_html=True
    )

    # Chat display area with fixed height and scrolling
    chat_container = st.container()
    with chat_container:
        st.markdown("""
            <style>
            .chat-container {
                height: 400px;
                overflow-y: auto;
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                margin-bottom: 15px;
            }
            </style>
            <div class="chat-container">
        """, unsafe_allow_html=True)

        display_chat_history()

        st.markdown("</div>", unsafe_allow_html=True)

    # User input
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Type your message:",
            key="user_message",
            height=70,
            placeholder=("Ask me anything..." if st.session_state.active_function == "regular"
                         else "Describe the financial transaction you want to perform...")
        )

        col1, col2 = st.columns([4, 1])
        with col2:
            submit_button = st.form_submit_button("Send")

    if submit_button and user_input.strip():
        # Process user input
        st.session_state.ai_chat_history.append({'role': 'user', 'content': user_input})

        # Get response based on active function
        if st.session_state.active_function == "regular":
            ai_response = ask_ai(user_input, api_url)
        else:
            ai_response = call_financial_tool_api(user_input, api_url)

        # Add AI response to chat history
        st.session_state.ai_chat_history.append({'role': 'assistant', 'content': ai_response})

        # Rerun to update UI
        st.rerun()