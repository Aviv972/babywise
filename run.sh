#!/bin/bash

# Find Python command (python3 or python)
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python is not installed"
    exit 1
fi

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi
$PYTHON_CMD src/server.py 