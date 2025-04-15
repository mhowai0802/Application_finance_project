import streamlit as st
import pandas as pd
import altair as alt
import logging
from utils.api import api_get, get_endpoint_url, test_auth_token

# Configure logger
logger = logging.getLogger("home")


def render(api_url):
    logger.info("Rendering home dashboard")
    st.title("Dashboard")

    # Check token validity if user is logged in
    token_valid = False
    if 'token' in st.session_state and st.session_state.token:
        token_valid = test_auth_token(api_url)
        if not token_valid:
            logger.warning("Token validation failed")
            st.warning("Your session appears to be invalid. Please log in again.")

    # Use placeholder data by default
    accounts = [
        {"account_id": 1, "account_name": "Checking Account", "account_type": "Checking", "balance": 5000,
         "currency": "HKD"},
        {"account_id": 2, "account_name": "Savings Account", "account_type": "Savings", "balance": 10000,
         "currency": "HKD"},
        {"account_id": 3, "account_name": "Investment Account", "account_type": "Investment", "balance": 15000,
         "currency": "HKD"}
    ]

    transactions = [
        {"transaction_id": 1, "source_account_id": 1, "destination_account_id": None, "amount": 200,
         "transaction_type": "Withdrawal", "transaction_date": "2025-04-01 14:30", "description": "ATM withdrawal",
         "status": "completed"},
        {"transaction_id": 2, "source_account_id": None, "destination_account_id": 2, "amount": 1000,
         "transaction_type": "Deposit", "transaction_date": "2025-04-05 09:15", "description": "Salary deposit",
         "status": "completed"},
        {"transaction_id": 3, "source_account_id": 1, "destination_account_id": 2, "amount": 500,
         "transaction_type": "Transfer", "transaction_date": "2025-04-10 16:45", "description": "Savings transfer",
         "status": "completed"}
    ]

    # Show API connection status
    with st.sidebar:
        st.markdown("---")
        st.caption("API Status")

        # Instead of checking the health endpoint, check the transactions endpoint
        # which we know exists
        api_status = "Connected"
        error_msg = None

        if token_valid:
            # If we have a valid token, check the transactions endpoint
            logger.info("Checking API connection via transactions endpoint")
            transactions_url = get_endpoint_url(api_url, "transactions", "history")
            test_response = api_get(transactions_url, {"limit": 1})

            if 'error' in test_response:
                api_status = "Error"
                error_msg = test_response['error']
                logger.error(f"API connection error: {error_msg}")
            else:
                api_status = "Connected"
                # Fetch real transaction data
                logger.info("Fetching transactions for dashboard")
                transactions_response = api_get(transactions_url, {"limit": 5})

                if 'error' not in transactions_response and 'transactions' in transactions_response:
                    logger.info(f"Successfully loaded {len(transactions_response['transactions'])} transactions")
                    transactions = transactions_response['transactions']
                    st.success("✓ Transaction data loaded")
                else:
                    if 'error' in transactions_response:
                        logger.error(f"Failed to load transactions: {transactions_response['error']}")
                        st.error(f"Error loading transactions: {transactions_response['error']}")
                    else:
                        logger.warning("Transactions response missing 'transactions' key")
                        st.warning("Couldn't parse transaction data")
        else:
            # If we don't have a valid token, show we're using demo data
            logger.info("No valid token - using demo data")
            api_status = "Demo Mode"

        # Display the API status
        if api_status == "Connected":
            st.success("✓ Backend API Connected")

            # Display authentication status
            if token_valid:
                st.success("✓ Authenticated")
            elif 'token' in st.session_state:
                st.error("✗ Authentication failed")
            else:
                st.info("Not logged in")
        elif api_status == "Demo Mode":
            st.info("Using demo data (not authenticated)")
        else:
            st.error(f"✗ API Error: {error_msg}")
            st.info("Using demo data for preview")

    # Dashboard layout
    col1, col2 = st.columns([2, 1])

    # Left column - Account Summary and Charts
    with col1:
        st.subheader("Account Summary")

        # Show account balances
        if accounts:
            total_balance = sum(float(acc.get('balance', 0)) for acc in accounts)

            # Create a DataFrame for the accounts
            df_accounts = pd.DataFrame(accounts)

            # Create a simple bar chart of account balances
            chart = alt.Chart(df_accounts).mark_bar().encode(
                x=alt.X('account_name', title='Account'),
                y=alt.Y('balance', title='Balance (HKD)'),
                color='account_name'
            ).properties(
                title=f'Total Balance: {total_balance:.2f} HKD'
            )
            st.altair_chart(chart, use_container_width=True)

            # Show account details in a table
            st.dataframe(
                df_accounts[['account_name', 'account_type', 'balance', 'currency']],
                use_container_width=True
            )
        else:
            st.info("No accounts found. Create an account to get started.")

    # Right column - Recent Transactions and Quick Actions
    with col2:
        st.subheader("Recent Transactions")

        if transactions:
            # Display recent transactions
            for transaction in transactions:
                with st.container():
                    transaction_type = transaction.get('transaction_type', 'Unknown')
                    amount = transaction.get('amount', 0)
                    description = transaction.get('description', 'No description')
                    date = transaction.get('transaction_date', 'Unknown date')

                    # Icons for different transaction types
                    icon = "↑" if transaction_type == 'Withdrawal' else "↓" if transaction_type == 'Deposit' else "↔"

                    # Color based on transaction type
                    amount_color = "red" if transaction_type == 'Withdrawal' else "green" if transaction_type == 'Deposit' else "blue"

                    st.markdown(f"{icon} **{transaction_type}** - {description}")
                    st.markdown(f"<span style='color:{amount_color};'>{amount} HKD</span> - {date}",
                                unsafe_allow_html=True)
                    st.markdown("---")
        else:
            st.info("No recent transactions")

        # Quick Actions
        st.subheader("Quick Actions")

        if st.button("➕ New Transaction", use_container_width=True):
            logger.info("User clicked New Transaction button")
            st.session_state.page = 'transactions'
            st.rerun()

        if st.button("🤖 Ask AI Assistant", use_container_width=True):
            logger.info("User clicked AI Assistant button")
            st.session_state.page = 'ai_assistant'
            st.rerun()


# Add this function to display log settings in the sidebar
def show_log_settings():
    with st.sidebar:
        st.markdown("---")
        st.caption("Logging")

        # Show current log level
        current_level = logging.getLevelName(logger.level)
        st.text(f"Current log level: {current_level}")

        # Option to change log level
        new_level = st.selectbox(
            "Change log level",
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            index=1  # Default to INFO
        )

        if st.button("Apply"):
            numeric_level = getattr(logging, new_level)
            logger.setLevel(numeric_level)
            # Also set API logger level
            logging.getLogger("api").setLevel(numeric_level)
            st.success(f"Log level set to {new_level}")