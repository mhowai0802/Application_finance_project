import streamlit as st
import requests
import json


def render(api_url):
    st.title("AI Financial Assistant")

    # Initialize chat history
    if 'ai_chat_history' not in st.session_state:
        st.session_state.ai_chat_history = []

    # Display chat history in a container with scrolling
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.ai_chat_history:
            if message['role'] == 'user':
                st.markdown(
                    f"<div style='background-color: #e6f7ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>You:</strong> {message['content']}</div>",
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>AI:</strong> {message['content']}</div>",
                    unsafe_allow_html=True)

    # Suggested questions
    if not st.session_state.ai_chat_history:
        st.subheader("Suggested Questions")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("What's my current balance?", use_container_width=True):
                ask_ai("What's my current balance?", api_url)

            if st.button("How much did I spend last month?", use_container_width=True):
                ask_ai("How much did I spend last month?", api_url)

        with col2:
            if st.button("What are my biggest expenses?", use_container_width=True):
                ask_ai("What are my biggest expenses?", api_url)

            if st.button("Can you help me create a savings plan?", use_container_width=True):
                ask_ai("Can you help me create a savings plan?", api_url)

    # Chat input
    with st.form("chat_input_form", clear_on_submit=True):
        user_input = st.text_input("Ask about your finances, transactions, or get help:", key="ai_input")
        submitted = st.form_submit_button("Send")

        if submitted and user_input:
            ask_ai(user_input, api_url)


def ask_ai(question, api_url):
    # Add user message to chat history
    st.session_state.ai_chat_history.append({
        'role': 'user',
        'content': question
    })

    # Send request to AI endpoint
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    response = requests.post(
        f"{api_url}/ai/chat",
        headers=headers,
        json={"message": question}
    )

    if response.status_code == 200:
        ai_response = response.json().get('response')

        # Add AI response to chat history
        st.session_state.ai_chat_history.append({
            'role': 'assistant',
            'content': ai_response
        })
    else:
        error_msg = "Failed to get response from AI assistant."
        st.session_state.ai_chat_history.append({
            'role': 'assistant',
            'content': error_msg
        })

    # Rerun to update the chat display
    st.experimental_rerun()