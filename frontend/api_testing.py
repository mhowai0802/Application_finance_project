import requests
import json
import sys
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:5000/api"  # Change if your API runs on a different URL
VERBOSE = True  # Set to True for detailed output, False for summary only

# Test user credentials
TEST_USER = {
    "username": "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S"),
    "email": "test@example.com",
    "password": "Test@123",
    "phone_number": "+85291234567"
}


# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text):
    if VERBOSE:
        print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def test_request(method, endpoint, data=None, headers=None, expected_status=200):
    """Make a request to the API and validate the response"""

    url = f"{API_BASE_URL}{endpoint}"
    print_info(f"Testing {method.upper()} {url}")

    try:
        if method.lower() == 'get':
            response = requests.get(url, params=data, headers=headers)
        elif method.lower() == 'post':
            response = requests.post(url, json=data, headers=headers)
        elif method.lower() == 'put':
            response = requests.put(url, json=data, headers=headers)
        elif method.lower() == 'delete':
            response = requests.delete(url, json=data, headers=headers)
        else:
            print_error(f"Unsupported method: {method}")
            return None

        if VERBOSE:
            print_info(f"Status: {response.status_code}")
            print_info(f"Response: {response.text[:300]}{'...' if len(response.text) > 300 else ''}")

        # Check if status code matches expected
        if response.status_code == expected_status:
            return response
        else:
            print_error(f"Expected status {expected_status}, got {response.status_code}")
            print_info(f"Response: {response.text}")
            return response

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return None


def test_health():
    """Test the health endpoint"""
    print_header("Testing Health Endpoint")

    response = test_request('get', '/health')
    if response and response.status_code == 200:
        print_success("Health endpoint is working")
        return True
    else:
        print_error("Health endpoint failed")
        return False


def test_auth():
    """Test authentication endpoints"""
    print_header("Testing Auth Endpoints")

    # Test registration
    print_info("\nTesting user registration...")
    reg_response = test_request('post', '/auth/register', data=TEST_USER)

    if not reg_response or reg_response.status_code != 200:
        print_error("Registration failed")
        return None

    reg_data = reg_response.json()
    mfa_secret = reg_data.get('mfa_secret')

    if mfa_secret:
        print_success("Registration successful")
        print_info(f"MFA Secret: {mfa_secret}")
    else:
        print_error("Registration successful but no MFA secret returned")
        return None

    # Test login
    print_info("\nTesting user login...")
    login_response = test_request('post', '/auth/login', data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    })

    if not login_response or login_response.status_code != 200:
        print_error("Login failed")
        return None

    login_data = login_response.json()

    if login_data.get('require_mfa'):
        print_success("Login successful, MFA required")
        user_id = login_data.get('user_id')

        # Simulate MFA verification (in a real test, you'd calculate the TOTP code)
        # This will likely fail as we don't have a valid TOTP code
        print_warning("MFA verification will likely fail as we don't have a valid TOTP code")
        print_info("\nTesting MFA verification...")
        mfa_response = test_request('post', '/auth/verify-mfa', data={
            "user_id": user_id,
            "mfa_token": "123456"  # This is likely wrong, but it's for testing the API structure
        }, expected_status=401)  # Expect 401 as our code is invalid

        if mfa_response:
            if mfa_response.status_code == 200:
                print_success("MFA verification successful (unexpected!)")
                token = mfa_response.json().get('token')
                return {"user_id": user_id, "token": token}
            else:
                print_warning("MFA verification failed as expected (invalid code)")
                return {"user_id": user_id, "token": None}
    else:
        token = login_data.get('token')
        if token:
            print_success("Login successful, no MFA required")
            return {"user_id": login_data.get('user_id'), "token": token}
        else:
            print_error("Login successful but no token returned")
            return None


def test_transactions(auth_data):
    """Test transaction endpoints"""
    print_header("Testing Transaction Endpoints")

    if not auth_data or not auth_data.get('token'):
        print_warning("Skipping transaction tests as we don't have a valid token")
        print_info("Attempting to test transaction endpoints without authentication...")

    headers = {}
    if auth_data and auth_data.get('token'):
        headers = {"Authorization": f"Bearer {auth_data.get('token')}"}

    # Test transaction history endpoint
    print_info("\nTesting transaction history...")
    history_response = test_request('get', '/transactions/history', headers=headers)

    if history_response and history_response.status_code == 200:
        print_success("Transaction history endpoint is accessible")
    else:
        print_error("Transaction history endpoint failed")

    # Test transaction initiation
    print_info("\nTesting transaction initiation...")
    transaction_data = {
        "source_account_id": 1,  # Using placeholder IDs since we don't have real accounts
        "destination_account_id": 2,
        "amount": 100.00,
        "transaction_type": "Transfer",
        "description": "API Test Transaction"
    }

    initiate_response = test_request('post', '/transactions/initiate',
                                     data=transaction_data,
                                     headers=headers)

    if not initiate_response or initiate_response.status_code not in [200, 201]:
        print_error("Transaction initiation failed")
        return

    transaction_id = initiate_response.json().get('transaction_id')
    if transaction_id:
        print_success("Transaction initiated successfully")

        # Test transaction verification
        print_info("\nTesting transaction verification...")
        verify_data = {
            "transaction_id": transaction_id,
            "mfa_token": "123456"  # This is likely wrong, but it's for testing the API structure
        }

        verify_response = test_request('post', '/transactions/verify',
                                       data=verify_data,
                                       headers=headers,
                                       expected_status=[200, 401])  # Accept either success or auth failure

        if verify_response:
            if verify_response.status_code == 200:
                print_success("Transaction verification successful")
            else:
                print_warning("Transaction verification failed (likely due to invalid MFA)")
    else:
        print_error("Transaction initiated but no ID returned")


def test_ai():
    """Test AI assistant endpoints"""
    print_header("Testing AI Assistant Endpoints")

    # Test AI question endpoint
    print_info("\nTesting AI assistant...")
    question_data = {
        "question": "What is my current balance?"
    }

    ai_response = test_request('post', '/ai/ask', data=question_data)

    if ai_response and ai_response.status_code == 200:
        print_success("AI assistant endpoint is accessible")
        response_text = ai_response.json().get('response')
        if response_text:
            print_info(f"AI Response: {response_text[:100]}...")
        else:
            print_warning("AI assistant returned no response text")
    else:
        print_error("AI assistant endpoint failed")


def main():
    print_header("API TESTING SCRIPT")
    print(f"Testing API at: {API_BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test health endpoint
    health_ok = test_health()

    if not health_ok:
        print_error("Health check failed. API may not be running.")
        sys.exit(1)

    # Test authentication
    auth_data = test_auth()

    # Test transactions
    test_transactions(auth_data)

    # Test AI assistant
    test_ai()

    print_header("TEST SUMMARY")
    print("API Testing Complete.")
    print("Note: Some tests may have failed if endpoints aren't fully implemented yet.")
    print("This script can help you track your progress as you build out your API.")


if __name__ == "__main__":
    main()