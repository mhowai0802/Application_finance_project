#!/bin/bash

# Start the backend server
echo "Starting Flask backend server..."
python backend/app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start the Streamlit frontend
echo "Starting Streamlit frontend..."
streamlit run frontend/app.py

# Kill the backend server when Streamlit is closed
kill $BACKEND_PID
