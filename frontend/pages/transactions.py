import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from utils.api import api_get, api_post, get_endpoint_url, test_auth_token
import requests

# Configure logger
logger = logging.getLogger("transactions")
logging.basicConfig(level=logging.INFO)


def render(api_url):
    logger.info("Rendering transactions page")
    st.title("Transactions")

    # Check if user is authenticated
    token_valid = False
    if 'token' in st.session_state and st.session_state.token:
        token_valid = test_auth_token(api_url)
        if not token_valid:
            st.warning("Your session appears to be invalid. Please log in again.")

    # Navigation tabs
    if 'transactions_view' not in st.session_state:
        st.session_state.transactions_view = 'new'

    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Transaction", use_container_width=True):
            st.session_state.transactions_view = 'new'
            st.rerun()
    with col2:
        if st.button("Transaction History", use_container_width=True):
            st.session_state.transactions_view = 'history'
            st.rerun()

    # Render the correct view
    if st.session_state.transactions_view == 'new':
        render_new_transaction_form(api_url, token_valid)
    elif st.session_state.transactions_view == 'mfa':
        render_mfa_verification(api_url, token_valid)
    elif st.session_state.transactions_view == 'history':
        render_transaction_history(api_url, token_valid)


def render_new_transaction_form(api_url, token_valid):
    st.subheader("Make a New Transaction")

    if not token_valid:
        st.warning("You need to be logged in to make transactions")
        st.info("For demo purposes, you can continue with sample data")

    # Demo accounts
    accounts = [
        {"account_id": 1, "account_name": "Checking Account", "balance": 5000, "currency": "HKD"},
        {"account_id": 2, "account_name": "Savings Account", "balance": 10000, "currency": "HKD"},
        {"account_id": 3, "account_name": "Investment Account", "balance": 15000, "currency": "HKD"}
    ]

    st.info("Using demo account data")

    with st.form("transaction_form"):
        # Source account selection
        source_options = {f"{acc['account_name']} ({acc['balance']} {acc['currency']})": acc['account_id']
                          for acc in accounts}
        source_account = st.selectbox("From Account", options=list(source_options.keys()))
        source_account_id = source_options[source_account]

        # Transaction details
        transaction_type = st.selectbox("Transaction Type", ["Transfer", "Withdrawal", "Deposit"])

        # Handle destination account based on transaction type
        destination_account_id = None
        if transaction_type == "Transfer":
            dest_options = {f"{acc['account_name']} ({acc['balance']} {acc['currency']})": acc['account_id']
                            for acc in accounts if acc['account_id'] != source_account_id}
            if dest_options:
                destination_account = st.selectbox("To Account", options=list(dest_options.keys()))
                destination_account_id = dest_options[destination_account]
            else:
                st.warning("You need at least two accounts to make a transfer.")
        elif transaction_type == "Deposit":
            # For deposits, we're receiving money, so source is None and destination is the selected account
            destination_account_id = source_account_id  # Using the selected account as destination
            source_account_id = None  # No source for deposits

        amount = st.number_input("Amount", min_value=0.01, format="%.2f")
        description = st.text_input("Description")

        submitted = st.form_submit_button("Continue")

        if submitted:
            # Create transaction data object
            transaction_data = {
                "amount": amount,
                "transaction_type": transaction_type,
                "description": description
            }

            # Only include account IDs that are not None
            if source_account_id is not None:
                transaction_data["source_account_id"] = source_account_id

            if destination_account_id is not None:
                transaction_data["destination_account_id"] = destination_account_id

            # Store in session state
            st.session_state.transaction_details = transaction_data

            # Debug view
            with st.expander("Debug Info", expanded=False):
                st.json(transaction_data)

            # Send to backend if authenticated
            if token_valid:
                token = st.session_state.token
                transaction_url = get_endpoint_url(api_url, "transactions", "initiate")

                try:
                    # Make API call
                    response = requests.post(
                        transaction_url,
                        json=transaction_data,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                    )

                    if response.status_code in [200, 201]:
                        # Success
                        response_data = response.json()
                        transaction_id = response_data.get('transaction_id')
                        st.success(f"Transaction initiated with ID: {transaction_id}")

                        # Store the transaction ID for verification
                        st.session_state.pending_transaction_id = transaction_id
                        st.session_state.transactions_view = 'mfa'
                        st.rerun()
                    else:
                        # Error handling
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('error', f"HTTP Error {response.status_code}")
                        except:
                            error_msg = f"HTTP Error {response.status_code}: {response.text}"

                        st.error(f"Transaction failed: {error_msg}")

                        # Common error guidance
                        if "account" in error_msg.lower():
                            st.info("Account IDs must match accounts in the database.")
                        elif "balance" in error_msg.lower():
                            st.info("There are insufficient funds for this transaction.")

                        # Fall back to demo mode
                        st.session_state.pending_transaction_id = 999
                        st.session_state.transactions_view = 'mfa'
                        st.rerun()

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    # Fall back to demo mode
                    st.session_state.pending_transaction_id = 999
                    st.session_state.transactions_view = 'mfa'
                    st.rerun()
            else:
                # Demo mode
                st.session_state.pending_transaction_id = 999
                st.session_state.transactions_view = 'mfa'
                st.rerun()


def render_mfa_verification(api_url, token_valid):
    st.subheader("Verify Transaction")
    st.info("Transaction initiated. Please verify with your MFA code.")

    # Show transaction details
    if 'transaction_details' in st.session_state:
        details = st.session_state.transaction_details
        st.write("Transaction Details:")
        st.write(f"Type: {details.get('transaction_type', 'N/A')}")
        st.write(f"Amount: {details.get('amount', 'N/A')} HKD")
        st.write(f"Description: {details.get('description', 'N/A')}")
    else:
        st.warning("Transaction details missing")

    with st.form("mfa_verification_form"):
        mfa_token = st.text_input("Enter MFA Code")
        mfa_submitted = st.form_submit_button("Verify and Complete Transaction")

        if mfa_submitted:
            transaction_id = st.session_state.get('pending_transaction_id')

            # Verify with backend if authenticated
            if token_valid:
                verify_data = {
                    "transaction_id": transaction_id,
                    "mfa_token": mfa_token
                }

                # Make API call
                verify_url = get_endpoint_url(api_url, "transactions", "verify-mfa")
                verify_response = api_post(verify_url, verify_data)

                if 'error' not in verify_response:
                    # Success
                    new_balance = verify_response.get('new_balance', 'Updated')
                    st.success(f"Transaction completed successfully! New balance: {new_balance} HKD")

                    # Reset and go to history
                    st.session_state.pending_transaction_id = None
                    st.session_state.transactions_view = 'history'
                    st.rerun()
                else:
                    # Error but simulate success for demo
                    st.error(f"Verification failed: {verify_response['error']}")
                    st.info("For demonstration, simulating a successful transaction.")

                    # Show simulated success
                    if 'transaction_details' in st.session_state:
                        details = st.session_state.transaction_details
                        new_balance = 5000 - float(details.get('amount', 0))
                        st.success(f"Transaction completed successfully! New balance: {new_balance} HKD")
                    else:
                        st.success(f"Transaction completed successfully!")

                    # Reset and go to history
                    st.session_state.pending_transaction_id = None
                    st.session_state.transactions_view = 'history'
                    st.rerun()
            else:
                # Demo mode - simulate success
                if 'transaction_details' in st.session_state:
                    details = st.session_state.transaction_details
                    new_balance = 5000 - float(details.get('amount', 0))
                    st.success(f"Transaction completed successfully! New balance: {new_balance} HKD")
                else:
                    st.success(f"Transaction completed successfully!")

                # Reset and go to history
                st.session_state.pending_transaction_id = None
                st.session_state.transactions_view = 'history'
                st.rerun()

    # Cancel button
    if st.button("Cancel Transaction"):
        if token_valid and 'pending_transaction_id' in st.session_state:
            # Try to cancel in backend
            cancel_url = get_endpoint_url(api_url, "transactions", "cancel")
            cancel_response = api_post(cancel_url, {"transaction_id": st.session_state.pending_transaction_id})

            if 'error' not in cancel_response:
                st.success("Transaction cancelled successfully")
            else:
                st.error(f"Could not cancel transaction: {cancel_response['error']}")
                st.info("Transaction cancelled locally")
        else:
            st.info("Transaction cancelled locally")

        # Reset transaction flow
        st.session_state.pending_transaction_id = None
        st.session_state.transactions_view = 'new'
        st.rerun()


def render_transaction_history(api_url, token_valid):
    st.subheader("Transaction History")

    # Set up filters
    col1, col2 = st.columns(2)
    with col1:
        transaction_types = ['All', 'Transfer', 'Withdrawal', 'Deposit']
        selected_type = st.selectbox('Filter by Type', transaction_types)
    with col2:
        status_options = ['All', 'completed', 'pending', 'failed', 'cancelled']
        selected_status = st.selectbox('Filter by Status', status_options)

    # Prepare filter params
    filter_params = {}
    if selected_type != 'All':
        filter_params['type'] = selected_type
    if selected_status != 'All':
        filter_params['status'] = selected_status

    # Default demo transactions
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

    # Try to get real transaction data if authenticated
    if 'token' in st.session_state:
        transactions_url = get_endpoint_url(api_url, "transactions", "history")
        response = api_get(transactions_url, filter_params)

        # Process the response
        if isinstance(response, dict) and 'error' in response:
            st.error(f"Error fetching transactions: {response['error']}")
            st.info("Showing demo transaction data.")
        elif isinstance(response, dict) and 'transactions' in response:
            transactions = response['transactions']
            st.success("Successfully loaded your transaction data")
        elif isinstance(response, list):
            transactions = response
            st.success("Successfully loaded your transaction data")
        else:
            st.warning("Received unexpected data format from API")
            st.info("Showing demo transaction data.")
    else:
        st.info("Using demo transaction data (please log in to see your actual transactions).")

    # Display transactions
    if transactions:
        df = pd.DataFrame(transactions)

        # Sort by date if available
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
            df = df.sort_values(by='transaction_date', ascending=False)

            # Format for display
            display_df = df.copy()
            display_df['transaction_date'] = display_df['transaction_date'].dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(display_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

        # Export option
        if st.button("Export to CSV"):
            csv = df.to_csv(index=False)
            filename = f"transaction_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=filename,
                mime="text/csv"
            )
    else:
        st.info("No transactions match the selected filters.")


# Add this to display in sidebar if needed
def show_log_status():
    with st.sidebar:
        st.markdown("---")
        st.caption("Logging Status")
        current_level = logging.getLevelName(logger.level)
        st.text(f"Current log level: {current_level}")

        new_level = st.selectbox(
            "Change Log Level",
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            index=1
        )

        if st.button("Update Log Level"):
            numeric_level = getattr(logging, new_level)
            logger.setLevel(numeric_level)
            logging.getLogger("api").setLevel(numeric_level)
            st.success(f"Log level set to {new_level}")