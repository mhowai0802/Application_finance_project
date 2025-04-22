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


def render_mfa_verification(api_url, token_valid, transaction_id=''):
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

    # --- Filter state management ---
    if 'selected_type' not in st.session_state:
        st.session_state.selected_type = 'All'
    if 'selected_status' not in st.session_state:
        st.session_state.selected_status = 'All'
    if 'filter_applied' not in st.session_state:
        st.session_state.filter_applied = False

    # --- Filter UI ---
    with st.form("transaction_filter_form"):
        col1, col2 = st.columns(2)
        with col1:
            transaction_types = ['All', 'Transfer', 'Withdrawal', 'Deposit']
            selected_type = st.selectbox('Filter by Type', transaction_types, index=transaction_types.index(st.session_state.selected_type))
        with col2:
            status_options = ['All', 'completed', 'pending', 'failed', 'cancelled']
            selected_status = st.selectbox('Filter by Status', status_options, index=status_options.index(st.session_state.selected_status))
        filter_button = st.form_submit_button("Apply Filter")

    # Update session state on filter apply
    if filter_button:
        st.session_state.selected_type = selected_type
        st.session_state.selected_status = selected_status
        st.session_state.filter_applied = True

    # Use the last applied filter for API query
    filter_params = {}
    if st.session_state.selected_type != 'All':
        filter_params['transaction_type'] = st.session_state.selected_type
    if st.session_state.selected_status != 'All':
        filter_params['status'] = st.session_state.selected_status

    # Demo transactions (fallback)
    transactions = []

    # Only fetch when filter is applied or on first load
    if st.session_state.filter_applied or not hasattr(render_transaction_history, "has_loaded"):
        render_transaction_history.has_loaded = True  # Static attribute to control initial load

        # Try to get real transaction data if authenticated
        if 'token' in st.session_state:
            transactions_url = get_endpoint_url(api_url, "transactions", "history")
            response = api_get(transactions_url, filter_params)

            if isinstance(response, dict) and 'error' in response:
                st.error(f"Error fetching transactions: {response['error']}")
                st.info("Showing demo transaction data.")
            elif isinstance(response, list):
                transactions = response
                st.success("Successfully loaded your transaction data")
        else:
            st.info("Using demo transaction data (please log in to see your actual transactions).")

        st.session_state.filter_applied = False

    # ---- Stylish Card Display ----
    if transactions:
        df = pd.DataFrame(transactions)
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
            df = df.sort_values(by='transaction_date', ascending=False)

        st.markdown("""
            <style>
            .txn-scroll-box {
                max-height: 500px;
                overflow-y: auto;
                padding-right: 8px;
                margin-bottom: 1em;
            }
            .txn-card {
                background: #f9fafb;
                border-radius: 10px;
                box-shadow: 0 1px 3px rgba(30,41,59,0.07);
                padding: 1em 1.5em 0.8em 1em;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1em;
            }
            .txn-icon {
                font-size: 2rem;
                margin-right: 1em;
                width: 2.5em;
                text-align: center;
            }
            .txn-desc {
                flex: 1;
            }
            .txn-amount-pos {
                color: #16a34a;
                font-weight: 700;
                font-size: 1.2em;
            }
            .txn-amount-neg {
                color: #ef4444;
                font-weight: 700;
                font-size: 1.2em;
            }
            .txn-status {
                padding: 0.1em 0.7em;
                border-radius: 6px;
                font-size: 0.9em;
                font-weight: 500;
                margin-left: 0.8em;
            }
            .txn-status.completed {background:#dcfce7; color:#15803d;}
            .txn-status.pending {background:#fef9c3; color:#a16207;}
            .txn-status.failed {background:#fee2e2; color:#b91c1c;}
            .txn-status.cancelled {background:#e0e7ef; color:#64748b;}
            @media (max-width: 600px) {
                .txn-card {flex-direction: column; align-items: flex-start;}
                .txn-amount-pos, .txn-amount-neg {margin-top:0.6em;}
            }
            </style>
        """, unsafe_allow_html=True)
        st.markdown('<div class="txn-scroll-box">', unsafe_allow_html=True)

        for _, row in df.iterrows():
            t_type = row.get('transaction_type', 'Other')
            icon = {
                "Deposit": "⬇️",
                "Withdrawal": "⬆️",
                "Transfer": "🔄"
            }.get(t_type, "💸")
            amount = row.get('amount', 0)
            amount_class = "txn-amount-pos" if t_type == "Deposit" else "txn-amount-neg"
            amount_prefix = "+" if t_type == "Deposit" else "-"
            amount_str = f"{amount_prefix}{abs(amount):,.2f} HKD"
            status = row.get('status', 'completed')
            status_class = f"txn-status {status}"

            desc = row.get('description', '')
            date_str = row.get('transaction_date')
            if isinstance(date_str, pd.Timestamp):
                date_str = date_str.strftime('%Y-%m-%d %H:%M')

            card_html = f"""
                <div class="txn-card">
                    <div class="txn-icon">{icon}</div>
                    <div class="txn-desc">
                        <div><strong>{t_type}</strong> &mdash; {desc}</div>
                        <div style="color:#64748b; font-size: 0.95em;">{date_str}</div>
                    </div>
                    <div>
                        <span class="{amount_class}">{amount_str}</span>
                        <span class="{status_class}">{status.capitalize()}</span>
                    </div>
                </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        # Export option
        with st.expander("Export Options"):
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