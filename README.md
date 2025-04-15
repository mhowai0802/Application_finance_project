# ExpenseShare HK

A secure financial transaction platform with integrated AI assistance designed for the Hong Kong market.

## Setup Instructions

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy .env.template to .env and configure your settings:
   ```
   cp .env.template .env
   ```
5. Set up the database:
   ```
   python backend/database/db_setup.py
   ```
6. Start the backend server:
   ```
   python backend/app.py
   ```
7. In a new terminal, start the frontend:
   ```
   streamlit run frontend/app.py
   ```

## Features

- Secure user authentication with MFA
- Transaction processing with MFA verification
- AI-powered financial assistant
- Account management and transaction history
