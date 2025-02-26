import asyncio
import pytest
from src.services.service_container import container
from src.utils.memory_utils import get_or_create_memory
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def test_baby_gear_agent_context():
    """Test context extraction and processing for baby gear agent"""
    try:
        # Initialize test session
        session_id = "test_gear_session"
        logger.info(f"Starting baby gear agent test with session_id: {session_id}")
        
        # Get memory components for the session
        thread_data = await get_or_create_memory(session_id, settings.database_url)
        logger.info("Memory components initialized")
        
        # Test message about stroller
        message = "I need a lightweight stroller for my 3-month-old with a budget of $500. We'll use it mainly for city walks and shopping."
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
        assert "budget" in context, f"Expected 'budget' in context, but got: {context}"
        assert "specific_needs" in context, f"Expected 'specific_needs' in context, but got: {context}"
        assert "usage_context" in context, f"Expected 'usage_context' in context, but got: {context}"
        
        # Verify field values
        assert context["baby_age"]["value"] == 3, "Incorrect baby age"
        assert context["budget"]["value"] == 500, "Incorrect budget"
        assert context["budget"]["currency"] == "USD", "Incorrect currency"
        
        # Test follow-up question
        message2 = "What features should I look for in a stroller for this age?"
        logger.info(f"Processing follow-up message: {message2}")
        
        result2 = await container.agent_factory.route_query(
            query=message2,
            session_id=session_id
        )
        
        # Verify context persisted
        context2 = thread_data["state"]["gathered_info"]
        logger.info(f"Updated context: {context2}")
        
        assert "baby_age" in context2, "Age info should persist in context"
        assert "budget" in context2, "Budget info should persist in context"
        
        logger.info("Baby gear agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Baby gear agent test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_baby_gear_agent_context()) 