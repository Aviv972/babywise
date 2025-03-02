#!/usr/bin/env python3
"""
Test script to diagnose workflow issues in the Babywise Chatbot
"""

import os
import sys
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the workflow module
from backend.workflow.workflow import get_workflow, memory_saver

def test_workflow():
    """Test the workflow with a simple message"""
    try:
        # Get the workflow
        workflow = get_workflow()
        logger.info("Successfully got workflow")
        
        # Create a test thread ID
        thread_id = "test_thread_" + datetime.now().strftime("%Y%m%d%H%M%S")
        logger.info(f"Created test thread ID: {thread_id}")
        
        # Create a test message
        message = "Hello, how are you?"
        human_message = HumanMessage(content=message)
        logger.info(f"Created test message: {message}")
        
        # Create a test state
        state = {
            "messages": [human_message],
            "context": {},
            "domain": "general",
            "extracted_entities": set(),
            "language": "en",
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "language": "en",
                "thread_id": thread_id
            },
            "user_context": {},
            "routines": {
                "sleep": [],
                "feeding": [],
                "diaper": []
            }
        }
        logger.info("Created test state")
        
        # Run the workflow with explicit thread_id configuration
        logger.info("Running workflow with thread_id configuration")
        result = workflow.invoke(state, config={"configurable": {"thread_id": thread_id}})
        logger.info("Workflow completed successfully")
        
        # Print the result
        logger.info(f"Result type: {type(result).__name__}")
        logger.info(f"Result keys: {result.keys() if hasattr(result, 'keys') else 'No keys'}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing workflow: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_workflow()
    if success:
        print("Workflow test completed successfully")
        sys.exit(0)
    else:
        print("Workflow test failed")
        sys.exit(1) 