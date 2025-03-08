#!/usr/bin/env python3
"""
Test script to diagnose workflow issues in the Babywise Chatbot
Includes both synchronous and asynchronous workflow testing
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the workflow module and components
from backend.workflow.workflow import get_workflow, memory_saver
from backend.workflow.extract_context import extract_context
from backend.workflow.select_domain import select_domain
from backend.workflow.generate_response import generate_response
from backend.workflow.post_process import post_process
from backend.models.message_types import HumanMessage, AIMessage

async def test_workflow_async():
    """Test the async workflow implementation"""
    try:
        logger.info("Starting async workflow test")
        
        # Create a test state
        test_state = {
            "messages": [
                HumanMessage(content="My 3-month-old baby isn't sleeping well at night. Any advice?")
            ],
            "context": {},
            "extracted_entities": set(),
            "domain": "general"
        }
        
        # Test extract_context
        logger.info("Testing extract_context function")
        context_state = await extract_context(test_state)
        logger.info(f"Context extraction complete. Entities: {context_state.get('extracted_entities', set())}")
        
        # Test select_domain
        logger.info("Testing select_domain function")
        domain_state = await select_domain(context_state)
        logger.info(f"Domain selection complete. Selected domain: {domain_state.get('domain', 'unknown')}")
        
        # Test generate_response (mock version to avoid API calls)
        logger.info("Testing generate_response function (mock version)")
        async def mock_generate_response(state):
            state["messages"].append(AIMessage(content="This is a mock response for testing purposes."))
            return state
            
        response_state = await mock_generate_response(domain_state)
        logger.info(f"Response generation complete. Response: {response_state['messages'][-1].content}")
        
        # Test post_process
        logger.info("Testing post_process function")
        final_state = await post_process(response_state)
        logger.info("Post-processing complete")
        
        return final_state
    except Exception as e:
        logger.error(f"Error in async workflow test: {str(e)}", exc_info=True)
        raise

async def test_redis_connectivity():
    """Test Redis connectivity"""
    try:
        logger.info("Testing Redis connectivity")
        from backend.services.redis_service import ensure_redis_initialized
        
        redis_status = await ensure_redis_initialized()
        logger.info(f"Redis connectivity: {'Connected' if redis_status else 'Disconnected'}")
        
        return redis_status
    except Exception as e:
        logger.error(f"Error testing Redis connectivity: {str(e)}", exc_info=True)
        return False

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

async def main():
    """Main test function"""
    logger.info("Starting Babywise workflow tests")
    
    # Test Redis connectivity
    redis_status = await test_redis_connectivity()
    logger.info(f"Redis connectivity test: {'Passed' if redis_status else 'Failed'}")
    
    # Test sync workflow
    sync_result = test_workflow()
    logger.info(f"Sync workflow test: {'Passed' if sync_result else 'Failed'}")
    
    # Test async workflow
    try:
        async_result = await test_workflow_async()
        logger.info(f"Async workflow test: {'Passed' if async_result else 'Failed'}")
    except Exception as e:
        logger.error(f"Async workflow test failed: {str(e)}")
        async_result = None
    
    # Print summary
    logger.info("\nTest Summary:")
    logger.info(f"Redis Connectivity: {'✓' if redis_status else '✗'}")
    logger.info(f"Sync Workflow: {'✓' if sync_result else '✗'}")
    logger.info(f"Async Workflow: {'✓' if async_result else '✗'}")
    
    # Determine overall success
    success = all([redis_status, sync_result, async_result is not None])
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 