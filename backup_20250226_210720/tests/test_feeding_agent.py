import asyncio
import pytest
from src.services.service_container import container
from src.utils.memory_utils import get_or_create_memory
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def test_feeding_agent_context():
    """Test context extraction and processing for feeding agent"""
    try:
        # Initialize test session
        session_id = "test_feeding_session"
        logger.info(f"Starting feeding agent test with session_id: {session_id}")
        
        # Get memory components for the session
        thread_data = await get_or_create_memory(session_id, settings.database_url)
        logger.info("Memory components initialized")
        
        # Test message about feeding schedule
        message = "My 6-month-old is exclusively breastfeeding every 3 hours during the day and I'm wondering about starting solids"
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
        assert "feeding_type" in context, f"Expected 'feeding_type' in context, but got: {context}"
        assert "current_schedule" in context, f"Expected 'current_schedule' in context, but got: {context}"
        
        # Verify field values
        assert context["baby_age"]["value"] == 6, "Incorrect baby age"
        assert context["feeding_type"] == "breastfeeding", "Incorrect feeding type"
        
        # Test follow-up question
        message2 = "How often should I feed solids at this age?"
        logger.info(f"Processing follow-up message: {message2}")
        
        result2 = await container.agent_factory.route_query(
            query=message2,
            session_id=session_id
        )
        
        # Verify context persisted
        context2 = thread_data["state"]["gathered_info"]
        logger.info(f"Updated context: {context2}")
        
        assert "baby_age" in context2, "Age info should persist in context"
        assert "feeding_type" in context2, "Feeding type should persist in context"
        
        logger.info("Feeding agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Feeding agent test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_feeding_agent_context()) 