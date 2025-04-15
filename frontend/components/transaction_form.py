import streamlit as st
import requests


def render_transaction_form(api_url, accounts, on_submit):
    """Render a reusable transaction form component"""

    if not accounts:
        st.warning("You don't have any accounts. Please create an account first.")
        return None

    # Source account selection
    source_options = {f"{acc['account_name']} ({acc['balance']} {acc['currency']})": acc['account_id'] for acc in
                      accounts}
    source_account = st.selectbox("From Account", options=list(source_options.keys()))
    source_account_id = source_options[source_account]

    # Transaction details
    transaction_type = st.selectbox("Transaction Type", ["Transfer", "Withdrawal", "Deposit"])

    # Destination account if it's a transfer
    destination_account_id = None
    if transaction_type == "Transfer":
        dest_options = {f"{acc['account_name']} ({acc['balance']} {acc['currency']})": acc['account_id']
                        for acc in accounts if acc['account_id'] != source_account_id}
        if dest_options:
            destination_account = st.selectbox("To Account", options=list(dest_options.keys()))
            destination_account_id = dest_options[destination_account]
        else:
            st.warning("You need at least two accounts to make a transfer.")
            return None

    amount = st.number_input("Amount", min_value=0.01, format="%.2f")
    description = st.text_input("Description")

    # Collect form data
    transaction_data = {
        "source_account_id": source_account_id,
        "destination_account_id": destination_account_id,
        "amount": amount,
        "transaction_type": transaction_type,
        "description": description
    }

    # Submit button
    if st.button("Continue"):
        on_submit(transaction_data)

    return transaction_data