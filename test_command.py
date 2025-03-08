#!/usr/bin/env python3
"""
Test script for command processing in Babywise Chatbot
"""

import requests
import json
import sys
from datetime import datetime

def test_command_processing(message, thread_id="test123", language="he"):
    """Test the command processing endpoint"""
    url = "http://localhost:8080/api/routine/process-command"
    
    payload = {
        "thread_id": thread_id,
        "message": message,
        "language": language
    }
    
    print(f"Sending request to {url} with payload: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("status") == "success":
                print("Command processed successfully!")
                if result.get("latest_event"):
                    print(f"Latest event: {json.dumps(result['latest_event'], indent=2, ensure_ascii=False)}")
            else:
                print(f"Error: {result.get('message', 'Unknown error')}")
        else:
            print(f"Request failed: {response.text}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_command.py 'התינוק הלך לישון ב 20:30'")
        return
    
    message = sys.argv[1]
    thread_id = sys.argv[2] if len(sys.argv) > 2 else "test123"
    language = sys.argv[3] if len(sys.argv) > 3 else "he"
    
    test_command_processing(message, thread_id, language)

if __name__ == "__main__":
    main() 