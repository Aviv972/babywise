#!/usr/bin/env python3
"""
Test script for validating the flow between user queries and event logging
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from backend.services.chat_service import process_chat
from backend.db.routine_tracker import get_events_by_date_range, get_latest_event

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

async def test_flow():
    """Test the flow between user queries and event logging"""
    try:
        thread_id = f"test_flow_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Starting flow test with thread_id: {thread_id}")
        
        # Step 1: User asks a question
        logger.info("\n\n--- STEP 1: User asks a question ---")
        result1 = await process_chat(
            thread_id=thread_id,
            message="My baby is 3 months old and having trouble sleeping through the night. What can I do?",
            language="en"
        )
        
        logger.info(f"Response to question: {result1['text'][:100]}...")
        logger.info(f"Domain: {result1['domain']}")
        logger.info(f"Context: {json.dumps(result1['context'], default=str)}")
        
        # Step 2: User logs an event
        logger.info("\n\n--- STEP 2: User logs an event ---")
        result2 = await process_chat(
            thread_id=thread_id,
            message="Baby went to sleep at 8:30pm",
            language="en"
        )
        
        logger.info(f"Response to event logging: {result2['text']}")
        
        # Check if the event was actually logged in the database
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today.replace(hour=23, minute=59, second=59)
        events = get_events_by_date_range(thread_id, today, tomorrow)
        
        if events:
            logger.info(f"Found {len(events)} events in the database:")
            for event in events:
                logger.info(f"  - {event['event_type']} event: {event['start_time']} to {event['end_time']}")
        else:
            logger.warning("No events found in the database!")
        
        # Step 3: User asks another question
        logger.info("\n\n--- STEP 3: User asks another question ---")
        result3 = await process_chat(
            thread_id=thread_id,
            message="How long should my 3-month-old sleep during the day?",
            language="en"
        )
        
        logger.info(f"Response to follow-up question: {result3['text'][:100]}...")
        logger.info(f"Domain: {result3['domain']}")
        logger.info(f"Context: {json.dumps(result3['context'], default=str)}")
        
        # Check if context was maintained
        if "baby_age" in result3["context"] and result3["context"]["baby_age"] == "3 months":
            logger.info("SUCCESS: Context was maintained between interactions!")
        else:
            logger.warning(f"Context may have been lost. Expected baby_age='3 months', got: {result3['context'].get('baby_age', 'not found')}")
        
        return {
            "success": True,
            "thread_id": thread_id,
            "context_maintained": "baby_age" in result3["context"] and result3["context"]["baby_age"] == "3 months"
        }
    
    except Exception as e:
        logger.error(f"Error in test_flow: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    asyncio.run(test_flow()) 