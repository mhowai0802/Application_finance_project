import sys
import os
import random
import datetime
from werkzeug.security import generate_password_hash
import mysql.connector
from mysql.connector import Error
import pyotp

# Add the parent directory to the path to import Config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import Config


def get_db_connection():
    """Create a connection to the database"""
    return mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )


def insert_sample_users():
    """Insert sample users into the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Sample user data
        users = [
            {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "password": "password123",
                "phone_number": "+85261234567"
            },
            {
                "username": "janedoe",
                "email": "jane.doe@example.com",
                "password": "password123",
                "phone_number": "+85269876543"
            },
            {
                "username": "davidwong",
                "email": "david.wong@example.com",
                "password": "password123",
                "phone_number": "+85298765432"
            },
            {
                "username": "sarahlee",
                "email": "sarah.lee@example.com",
                "password": "password123",
                "phone_number": "+85291234567"
            },
            {
                "username": "michaelchan",
                "email": "michael.chan@example.com",
                "password": "password123",
                "phone_number": "+85290123456"
            }
        ]

        # Insert users
        for user in users:
            # Generate MFA secret
            mfa_secret = pyotp.random_base32()

            # Hash password
            password_hash = generate_password_hash(user["password"])

            cursor.execute(
                """
                INSERT INTO users 
                (username, email, password_hash, phone_number, mfa_secret, last_login) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user["username"],
                    user["email"],
                    password_hash,
                    user["phone_number"],
                    mfa_secret,
                    datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
                )
            )

        conn.commit()
        print(f"✅ Inserted {len(users)} sample users")

        # Return user IDs for creating accounts
        cursor.execute("SELECT user_id FROM users")
        return [user_id[0] for user_id in cursor.fetchall()]

    except Error as e:
        print(f"❌ Error inserting users: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def insert_sample_accounts(user_ids):
    """Insert sample accounts for users"""
    if not user_ids:
        print("❌ No user IDs provided for creating accounts")
        return []

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        account_types = ["Checking", "Savings", "Investment", "Credit Card"]
        accounts = []

        # Create 1-3 accounts for each user
        for user_id in user_ids:
            num_accounts = random.randint(1, 3)

            for i in range(num_accounts):
                account_type = random.choice(account_types)

                # Generate account name based on type
                if i == 0:
                    account_name = f"Primary {account_type}"
                else:
                    account_name = f"{account_type} #{i}"

                # Generate random balance
                if account_type == "Credit Card":
                    balance = -1 * random.randint(100, 5000)
                else:
                    balance = random.randint(1000, 50000)

                cursor.execute(
                    """
                    INSERT INTO accounts
                    (user_id, account_name, account_type, balance, currency, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        account_name,
                        account_type,
                        balance,
                        "HKD",
                        datetime.datetime.now() - datetime.timedelta(days=random.randint(30, 365))
                    )
                )

                # Get the account ID for creating transactions
                account_id = cursor.lastrowid
                accounts.append({
                    "account_id": account_id,
                    "user_id": user_id,
                    "balance": balance
                })

        conn.commit()
        print(f"✅ Inserted {len(accounts)} sample accounts")
        return accounts

    except Error as e:
        print(f"❌ Error inserting accounts: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def insert_sample_transactions(accounts):
    """Insert sample transactions between accounts"""
    if not accounts:
        print("❌ No accounts provided for creating transactions")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        transaction_types = ["Transfer", "Withdrawal", "Deposit"]
        descriptions = [
            "Monthly salary", "Rent payment", "Grocery shopping", "Dinner with friends",
            "Movie tickets", "Utility bill", "Phone bill", "Internet bill",
            "Transportation", "Coffee shop", "Online shopping", "Gym membership",
            "Doctor's appointment", "Clothing purchase", "Electronics purchase",
            "Home supplies", "Restaurant", "Travel expenses", "Insurance payment",
            "Investment deposit", "Dividend payment", "ATM withdrawal"
        ]

        transactions_count = 0

        # Create 5-20 transactions per account
        for account in accounts:
            num_transactions = random.randint(5, 20)
            account_id = account["account_id"]
            user_id = account["user_id"]

            for _ in range(num_transactions):
                transaction_type = random.choice(transaction_types)
                amount = random.randint(10, 2000)
                description = random.choice(descriptions)

                # Transaction date within the last 90 days
                days_ago = random.randint(0, 90)
                transaction_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)

                source_account_id = None
                destination_account_id = None

                if transaction_type == "Transfer":
                    # Find another account (possibly belonging to another user)
                    other_accounts = [a for a in accounts if a["account_id"] != account_id]
                    if other_accounts:
                        other_account = random.choice(other_accounts)

                        # 50% chance of inbound or outbound transfer
                        if random.choice([True, False]):
                            source_account_id = account_id
                            destination_account_id = other_account["account_id"]
                        else:
                            source_account_id = other_account["account_id"]
                            destination_account_id = account_id
                    else:
                        # If no other accounts, default to withdrawal
                        transaction_type = "Withdrawal"
                        source_account_id = account_id

                elif transaction_type == "Withdrawal":
                    source_account_id = account_id

                elif transaction_type == "Deposit":
                    destination_account_id = account_id

                # Random status - mostly completed, some pending
                status = "completed" if random.random() < 0.9 else "pending"
                mfa_verified = status == "completed"

                cursor.execute(
                    """
                    INSERT INTO transactions
                    (source_account_id, destination_account_id, amount, transaction_type, 
                     transaction_date, description, status, mfa_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        source_account_id,
                        destination_account_id,
                        amount,
                        transaction_type,
                        transaction_date,
                        description,
                        status,
                        mfa_verified
                    )
                )
                transactions_count += 1

        conn.commit()
        print(f"✅ Inserted {transactions_count} sample transactions")

    except Error as e:
        print(f"❌ Error inserting transactions: {e}")
    finally:
        cursor.close()
        conn.close()


def main():
    """Main function to insert all sample data"""
    print("🔄 Inserting sample data into the ExpenseShare HK database...")

    # Insert users and get their IDs
    user_ids = insert_sample_users()

    # Insert accounts for those users
    accounts = insert_sample_accounts(user_ids)

    # Insert transactions between those accounts
    insert_sample_transactions(accounts)

    print("✅ Sample data insertion complete!")

    # Print test user credentials for easy login
    print("\n🔑 Test User Credentials:")
    print("Username: johndoe")
    print("Password: password123")
    print("MFA: You'll need to set up an authenticator app with the MFA secret for this user")
    print("Get the MFA secret by querying: SELECT username, mfa_secret FROM users WHERE username = 'johndoe';")


if __name__ == "__main__":
    main()