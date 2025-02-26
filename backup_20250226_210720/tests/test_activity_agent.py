import asyncio
import pytest
from src.services.service_container import container
from src.utils.memory_utils import get_or_create_memory
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def test_activity_agent_context():
    """Test context extraction and processing for activity agent"""
    try:
        # Initialize test session
        session_id = "test_activity_session"
        logger.info(f"Starting activity agent test with session_id: {session_id}")
        
        # Get memory components for the session
        thread_data = await get_or_create_memory(session_id, settings.database_url)
        logger.info("Memory components initialized")
        
        # Test message about activities
        message = "What indoor activities are good for my 8-month-old who loves music and is starting to crawl? We have a spacious living room."
        logger.info(f"Processing message: {message}")
        
        result = await container.agent_factory.route_query(
            query=message,
            session_id=session_id
        )
        
        # Verify context was saved
        context = thread_data["state"]["gathered_info"]
        logger.info(f"Extracted context: {context}")
        
        # Verify required fields
        assert "baby_age" in context, f"Expected 'baby_age' in context, but got: {context}"
        assert "activity_type" in context, f"Expected 'activity_type' in context, but got: {context}"
        assert "environment" in context, f"Expected 'environment' in context, but got: {context}"
        assert "preferences" in context, f"Expected 'preferences' in context, but got: {context}"
        assert "developmental_stage" in context, f"Expected 'developmental_stage' in context, but got: {context}"
        
        # Verify field values
        assert context["baby_age"]["value"] == 8, "Incorrect baby age"
        assert context["environment"]["type"] == "indoor", "Incorrect environment type"
        assert context["activity_type"]["type"] == "physical", "Incorrect activity type"
        
        # Test follow-up question
        message2 = "What other activities can we do to help with crawling?"
        logger.info(f"Processing follow-up message: {message2}")
        
        result2 = await container.agent_factory.route_query(
            query=message2,
            session_id=session_id
        )
        
        # Verify context persisted
        context2 = thread_data["state"]["gathered_info"]
        logger.info(f"Updated context: {context2}")
        
        assert "baby_age" in context2, "Age info should persist in context"
        assert "activity_type" in context2, "Activity type should persist in context"
        
        logger.info("Activity agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Activity agent test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_activity_agent_context()) 