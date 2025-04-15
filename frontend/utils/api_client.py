import requests
import json
import streamlit as st


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_headers(self):
        """Get headers with authorization token if available"""
        headers = {"Content-Type": "application/json"}
        if 'token' in st.session_state and st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        return headers

    def handle_response(self, response):
        """Handle API response and errors"""
        if response.status_code in (200, 201):
            return response.json()
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('error', 'Unknown error')
            except:
                error_message = f"HTTP Error: {response.status_code}"

            raise Exception(error_message)

    def get(self, endpoint, params=None):
        """Make a GET request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.get_headers(), params=params)
        return self.handle_response(response)

    def post(self, endpoint, data):
        """Make a POST request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.post(
            url,
            headers=self.get_headers(),
            data=json.dumps(data)
        )
        return self.handle_response(response)

    def put(self, endpoint, data):
        """Make a PUT request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.put(
            url,
            headers=self.get_headers(),
            data=json.dumps(data)
        )
        return self.handle_response(response)

    def delete(self, endpoint):
        """Make a DELETE request to the API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, headers=self.get_headers())
        return self.handle_response(response)