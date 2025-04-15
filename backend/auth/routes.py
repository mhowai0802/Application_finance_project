from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import config
from .utils import generate_mfa_secret, get_totp_uri, generate_qr_code, verify_totp
import jwt
import datetime

auth_bp = Blueprint('auth', __name__)


def get_db_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        print("Received data:", data)  # Debug log
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        phone_number = data.get('phone_number')

        if not all([username, email, password, phone_number]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate password length
        if len(password) < config.PASSWORD_MIN_LENGTH:
            return jsonify({'error': f'Password must be at least {config.PASSWORD_MIN_LENGTH} characters long'}), 400

        print("Password validation passed")  # Debug log

        # Hash password with bcrypt
        try:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256',
                                                   salt_length=config.BCRYPT_LOG_ROUNDS)
            print("Password hashed successfully")  # Debug log
        except Exception as e:
            print(f"Password hashing error: {str(e)}")
            return jsonify({'error': f'Password hashing error: {str(e)}'}), 500

        # Generate MFA secret
        try:
            mfa_secret = generate_mfa_secret()
            print("MFA secret generated")  # Debug log
        except Exception as e:
            print(f"MFA secret generation error: {str(e)}")
            return jsonify({'error': f'MFA secret generation error: {str(e)}'}), 500

        try:
            conn = get_db_connection()
            print("Database connection established")  # Debug log
            cursor = conn.cursor()

            # Insert new user
            query = "INSERT INTO users (username, email, password_hash, phone_number, mfa_secret) VALUES (%s, %s, %s, %s, %s)"
            values = (username, email, password_hash, phone_number, mfa_secret)
            print(f"Executing query: {query} with values: {values}")  # Debug log
            cursor.execute(query, values)
            conn.commit()
            user_id = cursor.lastrowid
            print(f"User inserted with ID: {user_id}")  # Debug log

            # Generate QR code for MFA setup
            totp_uri = get_totp_uri(username, mfa_secret)
            qr_code = generate_qr_code(totp_uri)
            print("QR code generated")  # Debug log

            return jsonify({
                'message': 'User registered successfully',
                'user_id': user_id,
                'qr_code': qr_code,
                'mfa_secret': mfa_secret  # In production, don't return this, just for setup
            }), 201

        except mysql.connector.Error as err:
            print(f"Database error: {str(err)}")  # Debug log
            return jsonify({'error': f'Database error: {str(err)}'}), 500
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()
            print("Connection closed")  # Debug log

    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    print(data)
    if not all([username, password]):
        return jsonify({'error': 'Missing username or password'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username, )
        )
        user = cursor.fetchone()
        print(user)
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        # Password is correct, now we need MFA
        return jsonify({
            'message': 'Password validated, MFA required',
            'user_id': user['user_id'],
            'require_mfa': True
        }), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/verify-mfa', methods=['POST'])
def verify_mfa():
    data = request.get_json()
    user_id = data.get('user_id')
    mfa_token = data.get('mfa_token')

    if not all([user_id, mfa_token]):
        return jsonify({'error': 'Missing user_id or MFA token'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT mfa_secret FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify the MFA token
        if verify_totp(user['mfa_secret'], mfa_token):
            # Update last login time
            cursor.execute(
                "UPDATE users SET last_login = NOW() WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()

            # Generate JWT token with expiration based on config
            token = jwt.encode({
                'user_id': user_id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=config.JWT_EXPIRATION_HOURS)
            }, config.SECRET_KEY)

            return jsonify({
                'message': 'Authentication successful',
                'token': token
            }), 200
        else:
            return jsonify({'error': 'Invalid MFA token'}), 401

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/user', methods=['GET'])
def get_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or 'Bearer ' not in auth_header:
        return jsonify({'error': 'Missing or invalid token'}), 401

    token = auth_header.replace('Bearer ', '')

    try:
        # Decode the token
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
        user_id = payload['user_id']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT user_id, username, email, phone_number, created_at, last_login FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify(user), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()