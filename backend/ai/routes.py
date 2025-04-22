from flask import Blueprint, request, jsonify
import mysql.connector
import config
import jwt
from functools import wraps
from ai.llama_client import generate_ai_response
from ai.llm_tools import execute_tools_directly
from langchain_core.tools import Tool
import re

ai_bp = Blueprint('ai', __name__)


def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'error': 'Token is invalid'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


@ai_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user_id):
    data = request.get_json()
    message = data.get('message')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    # Get user context data
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get user info
        cursor.execute(
            "SELECT username FROM users WHERE user_id = %s",
            (current_user_id,)
        )
        user = cursor.fetchone()

        # Get account information
        cursor.execute(
            "SELECT account_id, account_name, account_type, balance, currency FROM accounts WHERE user_id = %s",
            (current_user_id,)
        )
        accounts = cursor.fetchall()

        # Get recent transactions
        cursor.execute(
            """
            SELECT t.transaction_id, t.amount, t.transaction_type, t.description, t.transaction_date, t.status,
                   sa.account_name as source_account, da.account_name as destination_account
            FROM transactions t
            LEFT JOIN accounts sa ON t.source_account_id = sa.account_id
            LEFT JOIN accounts da ON t.destination_account_id = da.account_id
            WHERE sa.user_id = %s OR da.user_id = %s
            ORDER BY t.transaction_date DESC
            LIMIT 10
            """,
            (current_user_id, current_user_id)
        )
        transactions = cursor.fetchall()

        # Format context data for AI
        context = f"User: {user['username']}\n\nAccounts:\n"

        for account in accounts:
            context += f"- {account['account_name']} ({account['account_type']}): {account['balance']} {account['currency']}\n"

        context += "\nRecent Transactions:\n"
        for txn in transactions:
            source = txn['source_account'] if txn['source_account'] else 'External'
            destination = txn['destination_account'] if txn['destination_account'] else 'External'
            context += f"- {txn['transaction_date']}: {txn['amount']} from {source} to {destination} - {txn['description']} ({txn['status']})\n"

        # Detect if this might be a transaction request and use appropriate template
        is_transaction_intent = any(
            keyword in message.lower() for keyword in ["transfer", "send", "pay", "withdraw", "deposit"])
        template_name = 'transaction_help' if is_transaction_intent else 'financial_analysis'

        # Generate AI response
        ai_response = generate_ai_response(message, context, template_name)

        return jsonify({
            'response': ai_response
        }), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()



@ai_bp.route('/financial_tool', methods=['POST'])
@token_required
def financial_tool_endpoint(current_user_id):
    data = request.get_json()
    query = data.get('query')
    print(query)
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    result = execute_tools_directly(query)
    print(f"\nTool Execution Result: {result}")

    try:
        return jsonify({'answer': result}), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


