import streamlit as st
import requests
import json
from pages import home, login, register, transactions, ai_assistant
from components.sidebar import render_sidebar

# Configuration
API_URL = "http://localhost:5000/api"

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'user' not in st.session_state:
    st.session_state.user = None
if 'token' not in st.session_state:
    st.session_state.token = None


# Page navigation
def navigate_to(page):
    st.session_state.page = page


# App title
st.set_page_config(
    page_title="ExpenseShare HK",
    page_icon="💰",
    layout="wide"
)

# Render the appropriate page
if st.session_state.user is None:
    # User is not logged in
    if st.session_state.page == 'login':
        login.render(API_URL, navigate_to)
    elif st.session_state.page == 'register':
        register.render(API_URL, navigate_to)
    else:
        navigate_to('login')
else:
    # User is logged in, show sidebar navigation
    render_sidebar(navigate_to)

    # Render the selected page
    if st.session_state.page == 'home':
        home.render(API_URL)
    elif st.session_state.page == 'transactions':
        transactions.render(API_URL)
    elif st.session_state.page == 'ai_assistant':
        ai_assistant.render(API_URL)
    else:
        navigate_to('home')