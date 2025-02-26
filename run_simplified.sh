#!/bin/bash

# Run the simplified Babywise server
echo "Starting Babywise Chatbot Server..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Installing minimal dependencies..."
    pip install fastapi uvicorn langchain langchain-openai langgraph
fi

# Make sure the static directory exists
if [ ! -d "src/static" ]; then
    echo "Creating static directory..."
    mkdir -p src/static
fi

# Run the server
echo "Starting server..."
python -m uvicorn src.simplified_server:app --reload --host 0.0.0.0 --port 8000

# Deactivate the virtual environment when done
deactivate 