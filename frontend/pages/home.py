import streamlit as st
import pandas as pd
import altair as alt
import logging
from typing import List, Dict, Any, Optional

from utils.api import api_get, get_endpoint_url, test_auth_token

# --- Logging setup ---
logger = logging.getLogger("home")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

# --- Utility Functions ---

def get_demo_accounts() -> List[Dict[str, Any]]:
    """Return placeholder account data."""
    return [
        {"account_id": 1, "account_name": "Checking Account", "account_type": "Checking", "balance": 5000, "currency": "HKD"}
    ]

def get_demo_transactions() -> List[Dict[str, Any]]:
    """Return placeholder transaction data."""
    return [
        {"transaction_id": 1, "source_account_id": 1, "destination_account_id": None, "amount": 200,
         "transaction_type": "Withdrawal", "transaction_date": "2025-04-01 14:30", "description": "ATM withdrawal",
         "status": "completed"}
    ]

def fetch_accounts(api_url: str, token_valid: bool) -> List[Dict[str, Any]]:
    """Fetch accounts from API or return demo data."""
    if token_valid:
        accounts_url = get_endpoint_url(api_url, "transactions", "accounts")
        accounts = api_get(accounts_url, {"limit": 10})
        if isinstance(accounts, list) and accounts:
            logger.info("Fetched accounts from API")
            return accounts
        logger.warning("No accounts from API, using demo data")
    else:
        logger.info("Token invalid, using demo accounts")
    return get_demo_accounts()

def fetch_transactions(api_url: str, token_valid: bool) -> List[Dict[str, Any]]:
    """Fetch transactions from API or return demo data."""
    if token_valid:
        transactions_url = get_endpoint_url(api_url, "transactions", "history")
        transactions = api_get(transactions_url, {"limit": 5})
        if isinstance(transactions, list) and transactions:
            logger.info("Fetched transactions from API")
            return transactions
        logger.warning("No transactions from API, using demo data")
    else:
        logger.info("Token invalid, using demo transactions")
    return get_demo_transactions()

def show_api_status(api_url: str, token_valid: bool) -> bool:
    """Show API connection and authentication status in sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.caption("API Status")

        api_status = "Demo Mode"
        error_msg = None

        if token_valid:
            transactions_url = get_endpoint_url(api_url, "transactions", "history")
            test_response = api_get(transactions_url, {"limit": 1})
            if isinstance(test_response, dict) and 'error' in test_response:
                api_status = "Error"
                error_msg = test_response['error']
                logger.error(f"API connection error: {error_msg}")
            else:
                api_status = "Connected"
        else:
            logger.info("No valid token - using demo data")
            api_status = "Demo Mode"

        # Status display logic
        if api_status == "Connected":
            st.success("✓ Backend API Connected")
            st.success("✓ Authenticated")
            return True
        elif api_status == "Demo Mode":
            st.info("Using demo data (not authenticated)")
            return False
        else:
            st.error(f"✗ API Error: {error_msg}")
            st.info("Using demo data for preview")
            return False

def account_summary(df_accounts: pd.DataFrame):
    """Show account summary and bar chart."""
    total_balance = df_accounts['balance'].sum()
    chart = alt.Chart(df_accounts).mark_bar().encode(
        x=alt.X('account_name', title='Account'),
        y=alt.Y('balance', title='Balance (HKD)'),
        color='account_name'
    ).properties(
        title=f'Total Balance: {total_balance:.2f} HKD'
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(df_accounts[['account_name', 'account_type', 'balance', 'currency']], use_container_width=True)

def recent_transactions(transactions: List[Dict[str, Any]]):
    """Show recent transactions with formatting."""
    if not transactions:
        st.info("No recent transactions")
        return
    for transaction in transactions:
        with st.container():
            transaction_type = transaction.get('transaction_type', 'Unknown')
            amount = transaction.get('amount', 0)
            description = transaction.get('description', 'No description')
            date = transaction.get('transaction_date', 'Unknown date')
            # Icons and colors
            icon, color = {
                "Withdrawal": ("↑", "red"),
                "Deposit": ("↓", "green"),
            }.get(transaction_type, ("↔", "blue"))
            st.markdown(f"{icon} **{transaction_type}** - {description}")
            st.markdown(f"<span style='color:{color};'>{amount} HKD</span> - {date}", unsafe_allow_html=True)
            st.markdown("---")

def show_log_settings():
    """Display log level settings in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.caption("Logging")
        current_level = logging.getLevelName(logger.level)
        st.text(f"Current log level: {current_level}")
        new_level = st.selectbox(
            "Change log level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], index=1
        )
        if st.button("Apply"):
            numeric_level = getattr(logging, new_level)
            logger.setLevel(numeric_level)
            logging.getLogger("api").setLevel(numeric_level)
            st.success(f"Log level set to {new_level}")

# --- Main Render Function ---

def render(api_url: str):
    """Render the Streamlit dashboard for accounts and transactions."""
    logger.info("Rendering home dashboard")
    st.title("Dashboard")

    # Check token validity if user is logged in
    token_valid = False
    if st.session_state.get('token'):
        token_valid = test_auth_token(api_url)
        if not token_valid:
            logger.warning("Token validation failed")
            st.warning("Your session appears to be invalid. Please log in again.")

    show_log_settings()
    api_connected = show_api_status(api_url, token_valid)

    # Fetch data
    accounts = fetch_accounts(api_url, token_valid)
    transactions = fetch_transactions(api_url, token_valid)

    # --- Dashboard Layout ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Account Summary")
        if accounts:
            df_accounts = pd.DataFrame(accounts)
            account_summary(df_accounts)
        else:
            st.info("No accounts found. Create an account to get started.")

    with col2:
        st.subheader("Recent Transactions")
        recent_transactions(transactions)