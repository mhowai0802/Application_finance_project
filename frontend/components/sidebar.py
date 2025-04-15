import streamlit as st


def render_sidebar(navigate_to):
    with st.sidebar:
        st.title("ExpenseShare HK")

        # User info
        if st.session_state.user:
            st.write(f"Welcome, {st.session_state.user.get('username', 'User')}")

        st.markdown("---")

        # Navigation
        st.subheader("Navigation")

        if st.button("📊 Dashboard", use_container_width=True):
            navigate_to('home')

        if st.button("💸 Transactions", use_container_width=True):
            navigate_to('transactions')

        if st.button("🤖 AI Assistant", use_container_width=True):
            navigate_to('ai_assistant')

        st.markdown("---")

        # Logout button at bottom of sidebar
        if st.button("Logout", type="primary", use_container_width=True):
            st.session_state.user = None
            st.session_state.token = None
            navigate_to('login')
            st.experimental_rerun()