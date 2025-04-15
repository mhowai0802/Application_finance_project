from flask import Blueprint, request, jsonify
import mysql.connector
import config
from auth.utils import verify_totp
import jwt
from functools import wraps
import datetime
import decimal
from flask import jsonify
import mysql.connector

transactions_bp = Blueprint('transactions', __name__)


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


@transactions_bp.route('/initiate', methods=['POST'])
@token_required
def initiate_transaction(current_user_id):
    data = request.get_json()
    source_account_id = data.get('source_account_id')
    destination_account_id = data.get('destination_account_id')
    amount = data.get('amount')
    transaction_type = data.get('transaction_type')
    description = data.get('description')

    if not all([source_account_id, amount, transaction_type]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate transaction type
    if transaction_type not in config.TRANSACTION_TYPES:
        return jsonify(
            {'error': f'Invalid transaction type. Must be one of: {", ".join(config.TRANSACTION_TYPES)}'}), 400

    # Validate transaction amount
    if float(amount) > config.MAX_TRANSACTION_AMOUNT:
        return jsonify(
            {'error': f'Transaction amount exceeds the maximum limit of {config.MAX_TRANSACTION_AMOUNT}'}), 400

    # Verify the source account belongs to the current user
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM accounts WHERE account_id = %s AND user_id = %s",
            (source_account_id, current_user_id)
        )
        account = cursor.fetchone()

        if not account:
            return jsonify({'error': 'Invalid source account'}), 403

        # Check if sufficient balance
        if float(account['balance']) < float(amount):
            return jsonify({'error': 'Insufficient funds'}), 400

        # Create pending transaction
        cursor.execute(
            """
            INSERT INTO transactions 
            (source_account_id, destination_account_id, amount, transaction_type, description, status) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (source_account_id, destination_account_id, amount, transaction_type, description, 'pending')
        )
        conn.commit()
        transaction_id = cursor.lastrowid

        # Check if MFA is required based on amount threshold
        require_mfa = float(amount) >= config.REQUIRE_MFA_THRESHOLD

        return jsonify({
            'message': 'Transaction initiated, requires MFA verification' if require_mfa else 'Transaction initiated',
            'transaction_id': transaction_id,
            'require_mfa': require_mfa
        }), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@transactions_bp.route('/verify-mfa', methods=['POST'])
@token_required
def verify_transaction_mfa(current_user_id):
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    mfa_token = data.get('mfa_token')

    if not all([transaction_id, mfa_token]):
        return jsonify({'error': 'Missing transaction_id or MFA token'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get transaction details
        cursor.execute(
            """
            SELECT t.*, a.user_id, a.balance 
            FROM transactions t
            JOIN accounts a ON t.source_account_id = a.account_id
            WHERE t.transaction_id = %s
            """,
            (transaction_id,)
        )
        transaction = cursor.fetchone()

        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        # Verify the transaction belongs to the current user
        if transaction['user_id'] != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get user's MFA secret
        cursor.execute(
            "SELECT mfa_secret FROM users WHERE user_id = %s",
            (current_user_id,)
        )
        user = cursor.fetchone()

        # Verify the MFA token
        if verify_totp(user['mfa_secret'], mfa_token):
            # Update transaction status
            cursor.execute(
                "UPDATE transactions SET status = %s, mfa_verified = %s WHERE transaction_id = %s",
                ('completed', True, transaction_id)
            )

            # Update account balances
            source_balance = float(transaction['balance']) - float(transaction['amount'])
            cursor.execute(
                "UPDATE accounts SET balance = %s, last_updated = NOW() WHERE account_id = %s",
                (source_balance, transaction['source_account_id'])
            )

            # If there's a destination account, update its balance too
            if transaction['destination_account_id']:
                cursor.execute(
                    """
                    UPDATE accounts 
                    SET balance = balance + %s, last_updated = NOW() 
                    WHERE account_id = %s
                    """,
                    (transaction['amount'], transaction['destination_account_id'])
                )

            conn.commit()

            return jsonify({
                'message': 'Transaction completed successfully',
                'transaction_id': transaction_id,
                'new_balance': source_balance
            }), 200
        else:
            return jsonify({'error': 'Invalid MFA token'}), 401

    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@transactions_bp.route('/history', methods=['GET'])
@token_required
def get_transaction_history(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get all accounts owned by the user
        cursor.execute(
            "SELECT account_id FROM accounts WHERE user_id = %s",
            (current_user_id,)
        )
        accounts = cursor.fetchall()

        if not accounts:
            return jsonify([]), 200

        # Extract account IDs
        account_ids = [account['account_id'] for account in accounts]
        # Format the list for SQL IN clause
        account_ids_str = ', '.join(['%s'] * len(account_ids))

        # Get transactions where user's accounts are either source or destination
        query = f"""
        SELECT t.*, 
               sa.account_name as source_account_name,
               da.account_name as destination_account_name
        FROM transactions t
        LEFT JOIN accounts sa ON t.source_account_id = sa.account_id
        LEFT JOIN accounts da ON t.destination_account_id = da.account_id
        WHERE t.source_account_id IN ({account_ids_str}) 
           OR t.destination_account_id IN ({account_ids_str})
        ORDER BY t.transaction_date DESC
        """

        # Double the account_ids list because we use it twice in the query
        cursor.execute(query, account_ids + account_ids)
        transactions = cursor.fetchall()

        # Process the transactions to handle non-serializable types
        serializable_transactions = []
        for transaction in transactions:
            # Create a serializable version of each transaction
            serializable_transaction = {}
            for key, value in transaction.items():
                # Convert datetime objects to strings
                if isinstance(value, datetime.datetime):
                    serializable_transaction[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                # Convert Decimal objects to floats
                elif isinstance(value, decimal.Decimal):
                    serializable_transaction[key] = float(value)
                # Handle any other special types if needed
                else:
                    serializable_transaction[key] = value
            serializable_transactions.append(serializable_transaction)

        return jsonify(serializable_transactions), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@transactions_bp.route('/accounts', methods=['GET'])
@token_required
def get_user_accounts(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM accounts WHERE user_id = %s",
            (current_user_id,)
        )
        accounts = cursor.fetchall()

        return jsonify(accounts), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@transactions_bp.route('/accounts', methods=['POST'])
@token_required
def create_account(current_user_id):
    data = request.get_json()
    account_name = data.get('account_name')
    account_type = data.get('account_type')
    currency = data.get('currency', config.DEFAULT_CURRENCY)
    initial_balance = data.get('initial_balance', 0.00)

    if not all([account_name, account_type]):
        return jsonify({'error': 'Missing account name or type'}), 400

    # Validate account type
    if account_type not in config.ACCOUNT_TYPES:
        return jsonify({'error': f'Invalid account type. Must be one of: {", ".join(config.ACCOUNT_TYPES)}'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO accounts 
            (user_id, account_name, account_type, balance, currency) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (current_user_id, account_name, account_type, initial_balance, currency)
        )
        conn.commit()
        account_id = cursor.lastrowid

        return jsonify({
            'message': 'Account created successfully',
            'account_id': account_id
        }), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()