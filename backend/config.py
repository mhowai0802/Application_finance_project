# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask application settings
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_change_in_production')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '5000'))

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'joniwhfe')
DB_NAME = os.getenv('DB_NAME', 'fintech_app')

# Authentication settings
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
MFA_ISSUER_NAME = os.getenv('MFA_ISSUER_NAME', 'ExpenseShare HK')
PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))

# Transaction settings
TRANSACTION_TYPES = ['Transfer', 'Withdrawal', 'Deposit']
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'HKD')
MAX_TRANSACTION_AMOUNT = float(os.getenv('MAX_TRANSACTION_AMOUNT', '1000000'))
REQUIRE_MFA_THRESHOLD = float(os.getenv('REQUIRE_MFA_THRESHOLD', '0'))  # Amount above which MFA is required

# AI integration settings
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '2048'))
AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.7'))

# API endpoints
API_PREFIX = '/api'
AUTH_ENDPOINT = f"{API_PREFIX}/auth"
TRANSACTIONS_ENDPOINT = f"{API_PREFIX}/transactions"
AI_ENDPOINT = f"{API_PREFIX}/ai"

# Frontend URLs
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8501')

# Security settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', FRONTEND_URL).split(',')
BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', '12'))

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'app.log')

# Database table names
USERS_TABLE = 'users'
ACCOUNTS_TABLE = 'accounts'
TRANSACTIONS_TABLE = 'transactions'

# Database schema
DB_SCHEMA = {
    USERS_TABLE: """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            mfa_enabled BOOLEAN DEFAULT TRUE,
            mfa_secret VARCHAR(100) NULL
        )
    """,

    ACCOUNTS_TABLE: """
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            account_name VARCHAR(100) NOT NULL,
            account_type VARCHAR(50) NOT NULL,
            balance DECIMAL(15,2) DEFAULT 0.00,
            currency VARCHAR(3) DEFAULT 'HKD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """,

    TRANSACTIONS_TABLE: """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            source_account_id INT NULL,
            destination_account_id INT NULL,
            amount DECIMAL(15,2) NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            mfa_verified BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (source_account_id) REFERENCES accounts(account_id),
            FOREIGN KEY (destination_account_id) REFERENCES accounts(account_id)
        )
    """
}

# Account types
ACCOUNT_TYPES = ['Checking', 'Savings', 'Investment', 'Credit Card']

# AI assistant configuration
AI_PROMPT_TEMPLATES = {
    'financial_analysis': """
        Context: {context}

        User query: {prompt}

        Based on the financial data provided, analyze the user's finances and provide helpful insights or answer their question.

        Response:
    """,
    'transaction_help': """
        Context: {context}

        User query: {prompt}

        Help the user complete their transaction based on their request. Identify the transaction type, amount, and other details.

        Response:
    """
}