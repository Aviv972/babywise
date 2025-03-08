"""
Run a stroller query test for the Baby Wise system
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

class StrollerTest(unittest.TestCase):
    """Run a stroller query test for the Baby Wise system"""
    
    def setUp(self):
        """Set up test environment"""
        # Generate a unique thread ID for this test run
        self.thread_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"Using thread ID: {self.thread_id}")
    
    def test_stroller_query(self):
        """Test Case 1 (variant): Query about baby strollers"""
        # Send a query about baby strollers
        query = "What features should I look for in a baby stroller?"
        print(f"Sending query: {query}")
        
        try:
            response = requests.post(
                CHAT_ENDPOINT,
                json={
                    "message": query,
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
            
            # Check content of response for relevance
            response_text = data["response"]
            print(f"Response text: {response_text}")
            
            # Print whether the response contains relevant keywords
            keywords = ["stroller", "feature", "wheel", "safety", "comfort", "storage", "fold"]
            for keyword in keywords:
                if keyword in response_text.lower():
                    print(f"Found keyword: {keyword}")
            
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    unittest.main() 