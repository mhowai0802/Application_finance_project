#!/bin/bash
# run_dev.sh - Development script with hot reloading

# Set environment variables
export PYTHONPATH=$(pwd)
export API_URL="http://localhost:5000"

# Run streamlit with hot reloading enabled
streamlit run app.py --server.runOnSave=true --server.port=8501