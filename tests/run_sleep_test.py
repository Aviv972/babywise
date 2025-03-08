"""
Run a sleep event tracking test for the Baby Wise system
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

class SleepTest(unittest.TestCase):
    """Run a sleep event tracking test for the Baby Wise system"""
    
    def setUp(self):
        """Set up test environment"""
        # Generate a unique thread ID for this test run
        self.thread_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"Using thread ID: {self.thread_id}")
    
    def test_sleep_event_tracking(self):
        """Test Case 2: Save sleep event in Baby Tracker"""
        # Send a command to log a sleep event
        command = "My baby just fell asleep"
        print(f"Sending command: {command}")
        
        # Record current time for verification
        current_time = datetime.now()
        print(f"Current time: {current_time.isoformat()}")
        
        try:
            response = requests.post(
                CHAT_ENDPOINT,
                json={
                    "message": command,
                    "thread_id": self.thread_id,
                    "language": "en"
                }
            )
            
            print(f"Response status code: {response.status_code}")
            
            # Verify response
            self.assertEqual(response.status_code, 200, "Request should succeed")
            data = response.json()
            
            print(f"Response data: {json.dumps(data, indent=2)}")
            
            # Check that response contains relevant information
            self.assertIn("response", data, "Response should contain 'response' field")
            
            # Check if command was processed
            command_processed = data.get("command_processed", False)
            print(f"Command processed: {command_processed}")
            
            # Check command type
            command_type = data.get("command_type")
            print(f"Command type: {command_type}")
            
            # If command was processed, check the event in the database
            if command_processed and command_type == "sleep":
                # Give the system time to process
                time.sleep(1)
                
                print(f"Checking event in database...")
                try:
                    event_url = f"{ROUTINES_ENDPOINT}/events/latest/{self.thread_id}/sleep"
                    print(f"Requesting: {event_url}")
                    
                    event_response = requests.get(event_url)
                    print(f"Event response status code: {event_response.status_code}")
                    
                    if event_response.status_code == 200:
                        event_data = event_response.json()
                        print(f"Event data: {json.dumps(event_data, indent=2)}")
                        
                        # Verify event data
                        self.assertEqual(event_data.get("thread_id"), self.thread_id, 
                                        "Event should be associated with the test thread")
                        self.assertEqual(event_data.get("event_type"), "sleep", 
                                        "Event type should be sleep")
                        
                        # Verify timestamp is close to current time
                        event_time = datetime.fromisoformat(event_data.get("start_time").replace("Z", "+00:00"))
                        time_diff = abs((event_time - current_time).total_seconds())
                        print(f"Event time: {event_time.isoformat()}")
                        print(f"Time difference: {time_diff} seconds")
                        
                        self.assertLess(time_diff, 60, 
                                        "Event timestamp should be within 60 seconds of the request time")
                    else:
                        print(f"Failed to get event data: {event_response.text}")
                except Exception as e:
                    print(f"Error checking event: {e}")
            
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    unittest.main() 