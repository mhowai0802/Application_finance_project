import streamlit as st
import requests


def render_chat_interface(api_url, chat_history, on_submit):
    """Render a reusable chat interface component"""

    # Chat history display
    for message in chat_history:
        if message['role'] == 'user':
            st.markdown(
                f"<div style='background-color: #e6f7ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>You:</strong> {message['content']}</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>AI:</strong> {message['content']}</div>",
                unsafe_allow_html=True)

    # Input form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Type your message:", key="chat_input")
        submitted = st.form_submit_button("Send")

        if submitted and user_input:
            on_submit(user_input)

    # Suggested queries if chat is empty
    if not chat_history:
        st.markdown("#### Suggested Questions")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("What's my current balance?"):
                on_submit("What's my current balance?")

            if st.button("How much did I spend last month?"):
                on_submit("How much did I spend last month?")

        with col2:
            if st.button("What are my biggest expenses?"):
                on_submit("What are my biggest expenses?")

            if st.button("Can you help me create a savings plan?"):
                on_submit("Can you help me create a savings plan?")