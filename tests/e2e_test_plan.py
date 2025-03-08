"""
End-to-End Test Plan: Baby Tracker & Chat Query Interaction

This module implements automated tests for the Baby Wise system to verify
that it correctly handles both informational queries and baby tracking commands.
"""

import unittest
import requests
import json
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/api/chat"
ROUTINES_ENDPOINT = f"{API_BASE_URL}/api/routines"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

class BabyWiseE2ETests(unittest.TestCase):
    """End-to-End tests for the Baby Wise system"""
    
    def setUp(self):
        """Set up test environment"""
        # Check if server is running
        try:
            response = requests.get(HEALTH_ENDPOINT)
            if not response.ok:
                self.skipTest("Server is not available")
        except requests.RequestException:
            self.skipTest("Server is not available")
            
        # Generate a unique thread ID for this test run
        self.thread_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
    def tearDown(self):
        """Clean up after tests"""
        # Reset the chat thread
        try:
            requests.post(f"{API_BASE_URL}/api/chat/reset/{self.thread_id}")
        except:
            pass
    
    def test_baby_development_query(self):
        """Test Case 1: Query about baby feeding development"""
        # Send a query about baby feeding development
        query = "At what age can I introduce solid foods to my baby?"
        
        response = requests.post(
            CHAT_ENDPOINT,
            json={
                "message": query,
                "thread_id": self.thread_id,
                "language": "en"
            }
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200, "Request should succeed")
        data = response.json()
        
        # Check that response contains relevant information
        self.assertIn("response", data, "Response should contain 'response' field")
        self.assertFalse(data.get("command_processed", False), 
                         "This should not be processed as a command")
        
        # Check content of response for relevance
        response_text = data["response"]
        self.assertTrue(
            any(keyword in response_text.lower() for keyword in 
                ["month", "solid", "food", "baby", "introduce", "feeding", "development"]),
            "Response should contain relevant information about introducing solid foods"
        )
    
    def test_baby_stroller_query(self):
        """Test Case 1 (variant): Query about baby strollers"""
        # Send a query about baby strollers
        query = "What features should I look for in a baby stroller?"
        
        response = requests.post(
            CHAT_ENDPOINT,
            json={
                "message": query,
                "thread_id": self.thread_id,
                "language": "en"
            }
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200, "Request should succeed")
        data = response.json()
        
        # Check that response contains relevant information
        self.assertIn("response", data, "Response should contain 'response' field")
        self.assertFalse(data.get("command_processed", False), 
                         "This should not be processed as a command")
        
        # Check content of response for relevance
        response_text = data["response"]
        self.assertTrue(
            any(keyword in response_text.lower() for keyword in 
                ["stroller", "feature", "wheel", "safety", "comfort", "storage", "fold"]),
            "Response should contain relevant information about stroller features"
        )
    
    def test_sleep_event_tracking(self):
        """Test Case 2: Save sleep event in Baby Tracker"""
        # Send a command to log a sleep event
        command = "My baby just fell asleep"
        
        # Record current time for verification
        current_time = datetime.now()
        
        response = requests.post(
            CHAT_ENDPOINT,
            json={
                "message": command,
                "thread_id": self.thread_id,
                "language": "en"
            }
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200, "Request should succeed")
        data = response.json()
        
        # Check that response indicates command was processed
        self.assertIn("response", data, "Response should contain 'response' field")
        self.assertTrue(data.get("command_processed", False), 
                        "This should be processed as a command")
        self.assertEqual(data.get("command_type"), "sleep", 
                         "Command should be recognized as a sleep event")
        
        # Check that command data contains expected fields
        command_data = data.get("command_data", {})
        self.assertIn("event_id", command_data, "Response should include event_id")
        
        # Verify the event was stored in the database
        # Get the latest sleep event for this thread
        time.sleep(1)  # Give the system time to process
        
        response = requests.get(
            f"{ROUTINES_ENDPOINT}/events/latest/{self.thread_id}/sleep"
        )
        
        self.assertEqual(response.status_code, 200, "Request should succeed")
        event_data = response.json()
        
        # Verify event data
        self.assertEqual(event_data.get("thread_id"), self.thread_id, 
                         "Event should be associated with the test thread")
        self.assertEqual(event_data.get("event_type"), "sleep", 
                         "Event type should be sleep")
        
        # Verify timestamp is close to current time
        event_time = datetime.fromisoformat(event_data.get("start_time").replace("Z", "+00:00"))
        time_diff = abs((event_time - current_time).total_seconds())
        self.assertLess(time_diff, 60, 
                        "Event timestamp should be within 60 seconds of the request time")

if __name__ == "__main__":
    unittest.main() 