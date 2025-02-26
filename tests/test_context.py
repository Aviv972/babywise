import asyncio
import pytest
from src.services.service_container import container
from src.services.chat_session import ChatSession
from src.utils.memory_utils import get_or_create_memory
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def test_sleep_agent_context():
    """Test context saving and retrieval for sleep agent"""
    try:
        session_id = "test_sleep_session"
        logger.info(f"Starting sleep agent test with session_id: {session_id}")
        
        # Create chat session
        chat_session = ChatSession(session_id)
        
        # Add message to session
        message = "My 6-month-old baby usually naps three times a day, at 9am, 12pm, and 3pm"
        await chat_session.add_message("user", message)
        
        # Process message
        response = await chat_session.process_message(message)
        
        # Get context from session
        context = chat_session.session_data["gathered_info"]
        assert "baby_age" in context, f"Expected 'baby_age' in context, but got: {context}"
        assert "daily_routine" in context, f"Expected 'daily_routine' in context, but got: {context}"
        assert "nap_schedule" in context, f"Expected 'nap_schedule' in context, but got: {context}"
        
        logger.info("Sleep agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Sleep agent test failed: {str(e)}", exc_info=True)
        raise

async def test_feeding_agent_context():
    """Test context saving and retrieval for feeding agent"""
    try:
        session_id = "test_feeding_session"
        logger.info(f"Starting feeding agent test with session_id: {session_id}")
        
        # Create chat session
        chat_session = ChatSession(session_id)
        
        # Add message to session
        message = "My 6-month-old is exclusively breastfeeding every 3 hours during the day and I'm wondering about starting solids"
        await chat_session.add_message("user", message)
        
        # Process message
        response = await chat_session.process_message(message)
        
        # Get context from session
        context = chat_session.session_data["gathered_info"]
        assert "baby_age" in context, f"Expected 'baby_age' in context, but got: {context}"
        assert "feeding_type" in context, f"Expected 'feeding_type' in context, but got: {context}"
        assert "current_schedule" in context, f"Expected 'current_schedule' in context, but got: {context}"
        
        logger.info("Feeding agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Feeding agent test failed: {str(e)}", exc_info=True)
        raise

async def test_baby_gear_agent_context():
    """Test context saving and retrieval for baby gear agent"""
    try:
        session_id = "test_gear_session"
        logger.info(f"Starting baby gear agent test with session_id: {session_id}")
        
        # Create chat session
        chat_session = ChatSession(session_id)
        
        # Add message to session
        message = "I need a lightweight stroller for my 3-month-old with a budget of $500. We'll use it mainly for city walks and shopping."
        await chat_session.add_message("user", message)
        
        # Process message
        response = await chat_session.process_message(message)
        
        # Get context from session
        context = chat_session.session_data["gathered_info"]
        assert "baby_age" in context, f"Expected 'baby_age' in context, but got: {context}"
        assert "budget" in context, f"Expected 'budget' in context, but got: {context}"
        assert "specific_needs" in context, f"Expected 'specific_needs' in context, but got: {context}"
        
        logger.info("Baby gear agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Baby gear agent test failed: {str(e)}", exc_info=True)
        raise

async def test_activity_agent_context():
    """Test context saving and retrieval for activity agent"""
    try:
        session_id = "test_activity_session"
        logger.info(f"Starting activity agent test with session_id: {session_id}")
        
        # Create chat session
        chat_session = ChatSession(session_id)
        
        # Add message to session
        message = "What indoor activities are good for my 8-month-old who loves music and is starting to crawl? We have a spacious living room."
        await chat_session.add_message("user", message)
        
        # Process message
        response = await chat_session.process_message(message)
        
        # Get context from session
        context = chat_session.session_data["gathered_info"]
        assert "baby_age" in context, f"Expected 'baby_age' in context, but got: {context}"
        assert "environment" in context, f"Expected 'environment' in context, but got: {context}"
        assert "preferences" in context, f"Expected 'preferences' in context, but got: {context}"
        assert "developmental_stage" in context, f"Expected 'developmental_stage' in context, but got: {context}"
        
        logger.info("Activity agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Activity agent test failed: {str(e)}", exc_info=True)
        raise

async def test_context_persistence():
    """Test context persistence across messages and agents"""
    try:
        session_id = "test_context_session"
        logger.info(f"Starting context persistence test with session_id: {session_id}")
        
        # Create chat session
        chat_session = ChatSession(session_id)
        
        # Test case 1: Initial context extraction
        message1 = "I have 6-month-old twins and need help with sleep training"
        await chat_session.add_message("user", message1)
        response1 = await chat_session.process_message(message1)
        
        # Verify initial context
        context1 = chat_session.session_data["gathered_info"]
        assert "baby_age" in context1, "Baby age not extracted"
        assert context1["baby_age"]["value"] == 6, "Incorrect baby age"
        
        # Test case 2: Context persistence in follow-up
        message2 = "They wake up every 2 hours at night"
        await chat_session.add_message("user", message2)
        response2 = await chat_session.process_message(message2)
        
        # Verify context is maintained and updated
        context2 = chat_session.session_data["gathered_info"]
        assert "baby_age" in context2, "Baby age not persisted"
        assert "sleep_pattern" in context2, "Sleep pattern not extracted"
        
        # Test case 3: Agent transition with context
        message3 = "What kind of double stroller would you recommend?"
        await chat_session.add_message("user", message3)
        response3 = await chat_session.process_message(message3)
        
        # Verify context persists across agents
        context3 = chat_session.session_data["gathered_info"]
        assert "baby_age" in context3, "Baby age lost in transition"
        assert context3["baby_age"]["value"] == 6, "Baby age changed"
        
        logger.info("Context persistence test completed successfully")
        
    except Exception as e:
        logger.error(f"Context persistence test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_sleep_agent_context())
    asyncio.run(test_feeding_agent_context())
    asyncio.run(test_baby_gear_agent_context())
    asyncio.run(test_activity_agent_context())
    asyncio.run(test_context_persistence()) 