"""
Run a direct command test for the Baby Wise system
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

class DirectCommandTest(unittest.TestCase):
    """Run a direct command test for the Baby Wise system"""
    
    def setUp(self):
        """Set up test environment"""
        # Generate a unique thread ID for this test run
        self.thread_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"Using thread ID: {self.thread_id}")
    
    def test_direct_sleep_command(self):
        """Test with a more direct sleep command"""
        # Send a direct command to log a sleep event
        command = "Log a sleep event starting now"
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
            
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    unittest.main() 