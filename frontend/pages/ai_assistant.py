import streamlit as st
import requests
import json
import streamlit as st
import requests
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage


def render(api_url):
    st.title("AI Financial Assistant")

    # Initialize chat history if not exists
    if 'ai_chat_history' not in st.session_state:
        st.session_state.ai_chat_history = []

    # Create tabs for different AI functions
    tab1, tab2 = st.tabs(["Regular AI", "Financial Analysis Tool"])

    # Track which tab/function is active
    if 'active_function' not in st.session_state:
        st.session_state.active_function = "regular"

    # Set active function based on tab selection
    with tab1:
        if st.button("Use Regular AI", key="use_regular"):
            st.session_state.active_function = "regular"
            st.rerun()

    with tab2:
        if st.button("Use Financial Tool", key="use_financial"):
            st.session_state.active_function = "financial"
            st.rerun()

    # Display current mode
    st.write(f"Current mode: {st.session_state.active_function.title()}")

    # Add a clear chat button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Clear Chat", key="clear_chat"):
            st.session_state.ai_chat_history = []
            st.rerun()

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

    # Chat input - single input for both functions
    user_input = st.text_input("Ask a question:", key="input")
    if st.button("Send", key="send"):
        if user_input:
            # Add user message to chat history
            st.session_state.ai_chat_history.append({'role': 'user', 'content': user_input})

            # Process based on active function
            if st.session_state.active_function == "regular":
                # Regular AI function (ask_ai)
                ai_response = ask_ai(user_input, api_url)
            else:
                # Financial analysis tool
                ai_response = call_financial_tool_api(user_input, api_url)

            # Add AI response to chat history
            st.session_state.ai_chat_history.append({'role': 'assistant', 'content': ai_response})

            # Clear the input box after sending
            st.session_state.input = ""

            # Rerun to update UI
            st.rerun()



def ask_ai(question, api_url):

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
    st.rerun()


def call_financial_tool_api(query, api_url):
    """Call the financial tool endpoint on the backend"""
    response = requests.post(
        f"{api_url}/auth/verify-mfa",
        json={
            "user_id": st.session_state.temp_user_id,
            "mfa_token": st.session_state.mfa_token
        }
    )
    try:
        response = requests.post(f"{api_url}/financial_tool", json={"query": query})
        if response.status_code == 200:
            data = response.json()

            # If the backend suggests forwarding to regular AI
            if data.get('forward_to_regular_ai', False):
                return f"Financial Tool: {data.get('response')}\n\nLet me check with the regular AI...\n\n{ask_ai(query, api_url)}"
            else:
                return data.get('response', 'No response from API')
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

