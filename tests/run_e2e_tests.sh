#!/bin/bash

# End-to-End Test Runner for Baby Wise
# This script runs the automated end-to-end tests for the Baby Wise system

# Set up environment
echo "Setting up test environment..."
source ../.env 2>/dev/null || echo "No .env file found, using default settings"

# Check if server is running
echo "Checking if server is running..."
if ! curl -s "$API_BASE_URL/health" > /dev/null; then
    echo "Server is not running. Starting server..."
    # Start server in background
    cd ..
    python run_server.py &
    SERVER_PID=$!
    
    # Wait for server to start
    echo "Waiting for server to start..."
    for i in {1..10}; do
        if curl -s "$API_BASE_URL/health" > /dev/null; then
            echo "Server started successfully."
            break
        fi
        
        if [ $i -eq 10 ]; then
            echo "Failed to start server. Exiting."
            exit 1
        fi
        
        echo "Waiting... ($i/10)"
        sleep 2
    done
    
    # Set flag to kill server when done
    KILL_SERVER=true
else
    echo "Server is already running."
    KILL_SERVER=false
fi

# Run tests
echo "Running end-to-end tests..."
python e2e_test_plan.py

# Capture test result
TEST_RESULT=$?

# Clean up
if [ "$KILL_SERVER" = true ]; then
    echo "Stopping server..."
    kill $SERVER_PID
fi

echo "Tests completed with exit code: $TEST_RESULT"
exit $TEST_RESULT 