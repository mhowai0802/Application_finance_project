import requests
import streamlit as st
import logging

# Configure logger
logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO)

# API Endpoint mapping - only use endpoints that exist in your backend
API_ENDPOINTS = {
    "auth": "/auth",
    "transactions": "/transactions",
    "ai": "/ai",
    "health": "/health"
}


def get_endpoint_url(api_url, endpoint_key, sub_path=""):
    """Build the full URL for an API endpoint"""
    # Make sure api_url doesn't end with a slash and has /api
    if api_url.endswith('/'):
        api_url = api_url[:-1]

    # Make sure api_url has /api
    if not api_url.endswith('/api'):
        api_url = f"{api_url}/api"

    base_endpoint = API_ENDPOINTS.get(endpoint_key, f"/{endpoint_key}")
    if sub_path:
        # Add leading slash to sub_path if it doesn't have one
        if not sub_path.startswith('/'):
            sub_path = f"/{sub_path}"
        return f"{api_url}{base_endpoint}{sub_path}"
    return f"{api_url}{base_endpoint}"


def get_auth_header():
    """Get the authorization header with token"""
    token = st.session_state.get('token')
    if not token:
        logger.debug("No auth token available in session state")
        return {}
    logger.debug(f"Using auth token from session state (first 10 chars): {token[:10]}...")
    return {"Authorization": f"Bearer {token}"}


def handle_api_error(response):
    """Handle API error responses"""
    try:
        error_data = response.json()
        error_msg = error_data.get('error', f"HTTP {response.status_code}: {response.reason}")
        logger.error(f"API error: {error_msg}")
        return error_msg
    except:
        error_msg = f"HTTP {response.status_code}: {response.text or response.reason}"
        logger.error(f"API error: {error_msg}")
        return error_msg


def api_get(url, params=None, timeout=5):
    """Make a GET request to the API with error handling and timeout"""
    # Get token from session state
    token = st.session_state.get('token')
    headers = {}

    # Add token to headers if it exists
    if token:
        headers["Authorization"] = f"Bearer {token}"
        token_preview = token[:10] + "..." if len(token) > 10 else token
        logger.debug(f"Using token in request: {token_preview}")
    else:
        logger.debug("No token available for request")

    # Log API call
    logger.info(f"GET {url}")
    if params:
        logger.debug(f"GET params: {params}")

    try:
        logger.debug(f"Making request with headers: {headers}")
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        logger.debug(f"Response status: {response.status_code}")

        if response.status_code == 200:
            try:
                json_data = response.json()
                logger.debug(f"Response JSON type: {type(json_data)}")
                if isinstance(json_data, dict):
                    logger.debug(f"Response JSON keys: {list(json_data.keys())}")
                elif isinstance(json_data, list):
                    logger.debug(f"Response is a JSON array with {len(json_data)} items")
                return json_data
            except ValueError:
                logger.error(f"Response not JSON: {response.text[:100]}")
                return {"error": "Invalid JSON response"}
        else:
            error_msg = f"HTTP Error {response.status_code}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    error_msg = error_data['error']
            except:
                if response.text:
                    error_msg = f"{error_msg}: {response.text}"

            logger.error(f"API error: {error_msg}")

            if response.status_code == 401:
                logger.warning("Authentication failed (401 Unauthorized)")

            return {"error": error_msg}
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out: {url}")
        return {"error": "Request timed out. The API server might be down or unreachable."}
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: {url}")
        return {"error": "Connection error. The API server might be down or unreachable."}
    except Exception as e:
        logger.error(f"Request exception: {str(e)}")
        return {"error": str(e)}


def api_post(url, data=None, timeout=5):
    """Make a POST request to the API with error handling and timeout"""
    # Get token from session state
    token = st.session_state.get('token')
    headers = {"Content-Type": "application/json"}

    # Add token to headers if it exists
    if token:
        headers["Authorization"] = f"Bearer {token}"
        token_preview = token[:10] + "..." if len(token) > 10 else token
        logger.debug(f"Using token in request: {token_preview}")
    else:
        logger.debug("No token available for request")

    # Log API call
    logger.info(f"POST {url}")
    if data:
        # Don't log sensitive data like passwords
        safe_data = {k: v if k not in ['password', 'mfa_token'] else '[REDACTED]' for k, v in data.items()}
        logger.debug(f"POST data: {safe_data}")

    try:
        logger.debug(f"Making request with headers: {headers}")
        response = requests.post(url, json=data, headers=headers, timeout=timeout)
        status = response.status_code
        logger.debug(f"Response status: {status}")

        # Log the raw response for debugging
        try:
            logger.debug(f"Response text: {response.text[:500]}")
        except:
            logger.debug("Could not log response text")

        if status in [200, 201]:
            try:
                json_data = response.json()
                logger.debug(f"Response JSON type: {type(json_data)}")
                if isinstance(json_data, dict):
                    logger.debug(f"Response JSON keys: {list(json_data.keys())}")
                elif isinstance(json_data, list):
                    logger.debug(f"Response is a JSON array with {len(json_data)} items")

                # If this is a login response, save the token
                if 'token' in json_data and url.endswith('/auth/login'):
                    logger.info("Login successful, saving token to session state")
                    st.session_state.token = json_data['token']

                return json_data
            except ValueError:
                logger.error(f"Response not JSON: {response.text[:100]}")
                return {"error": "Invalid JSON response"}
        else:
            error_msg = f"HTTP Error {status}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and 'error' in error_data:
                    error_msg = error_data['error']
            except:
                if response.text:
                    error_msg = f"{error_msg}: {response.text}"

            logger.error(f"API error: {error_msg}")

            if status == 401:
                logger.warning("Authentication failed (401 Unauthorized)")

            return {"error": error_msg}
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out: {url}")
        return {"error": "Request timed out. The API server might be down or unreachable."}
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: {url}")
        return {"error": "Connection error. The API server might be down or unreachable."}
    except Exception as e:
        logger.error(f"Request exception: {str(e)}")
        return {"error": str(e)}


def test_auth_token(api_url):
    """Test if the current auth token is valid"""
    token = st.session_state.get('token')
    if not token:
        logger.debug("No token to test")
        return False

    # Log the token details for debugging (first few characters only)
    token_preview = token[:10] + "..." if len(token) > 10 else token
    logger.debug(f"Testing token validity: {token_preview}")

    # Make a simple test request to check token validity
    test_url = get_endpoint_url(api_url, "transactions", "history")
    logger.debug(f"Testing token with URL: {test_url}")

    # Get the auth header and log it
    headers = {"Authorization": f"Bearer {token}"}
    logger.debug(f"Using Authorization header: Bearer {token_preview}...")

    try:
        # Use requests directly to get more control
        response = requests.get(test_url, headers=headers, timeout=5)
        logger.debug(f"Token test response status: {response.status_code}")

        if response.status_code == 200:
            logger.debug("Token is valid")
            return True
        else:
            logger.warning(f"Token test failed with status code: {response.status_code}")
            # Log response for debugging
            try:
                response_data = response.json()
                logger.debug(f"Response data: {response_data}")
            except:
                logger.debug(f"Response text: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error testing token: {str(e)}")
        return False