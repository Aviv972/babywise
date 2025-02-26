import asyncio
import pytest
from src.services.service_container import container
from src.utils.memory_utils import get_or_create_memory
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

async def test_budget_agent():
    """Test context extraction and processing for budget agent"""
    try:
        session_id = "test_budget_session"
        logger.info(f"Starting budget agent test with session_id: {session_id}")
        
        thread_data = await get_or_create_memory(session_id, settings.database_url)
        
        # Test message with budget and timeframe
        message = "I need help planning a budget of $1500 per month for baby essentials and gear. We need a stroller urgently."
        logger.info(f"Processing message: {message}")
        
        result = await container.agent_factory.route_query(
            query=message,
            session_id=session_id
        )
        
        # Verify context extraction
        context = thread_data["state"]["gathered_info"]
        logger.info(f"Extracted context: {context}")
        
        # Verify required fields
        assert "budget_range" in context, "Budget range not extracted"
        assert context["budget_range"]["value"] == 1500, "Incorrect budget value"
        assert context["budget_range"]["currency"] == "USD", "Incorrect currency"
        assert "timeframe" in context, "Timeframe not extracted"
        assert "priority_needs" in context, "Priority needs not extracted"
        
        logger.info("Budget agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Budget agent test failed: {str(e)}", exc_info=True)
        raise

async def test_pregnancy_agent():
    """Test context extraction and processing for pregnancy agent"""
    try:
        session_id = "test_pregnancy_session"
        logger.info(f"Starting pregnancy agent test with session_id: {session_id}")
        
        thread_data = await get_or_create_memory(session_id, settings.database_url)
        
        # Test message with pregnancy week and symptoms
        message = "I'm 20 weeks pregnant and experiencing some nausea and fatigue. What should I expect at this stage?"
        logger.info(f"Processing message: {message}")
        
        result = await container.agent_factory.route_query(
            query=message,
            session_id=session_id
        )
        
        # Verify context extraction
        context = thread_data["state"]["gathered_info"]
        logger.info(f"Extracted context: {context}")
        
        # Verify required fields
        assert "pregnancy_week" in context, "Pregnancy week not extracted"
        assert context["pregnancy_week"]["value"] == 20, "Incorrect week value"
        assert "symptoms" in context, "Symptoms not extracted"
        assert len(context["symptoms"]) > 0, "No symptoms extracted"
        
        logger.info("Pregnancy agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Pregnancy agent test failed: {str(e)}", exc_info=True)
        raise

async def test_travel_agent():
    """Test context extraction and processing for travel agent"""
    try:
        session_id = "test_travel_session"
        logger.info(f"Starting travel agent test with session_id: {session_id}")
        
        thread_data = await get_or_create_memory(session_id, settings.database_url)
        
        # Test message with travel details
        message = "Planning a 5-day flight trip with my 4-month-old baby to visit family in New York. Need advice on flying with an infant."
        logger.info(f"Processing message: {message}")
        
        result = await container.agent_factory.route_query(
            query=message,
            session_id=session_id
        )
        
        # Verify context extraction
        context = thread_data["state"]["gathered_info"]
        logger.info(f"Extracted context: {context}")
        
        # Verify required fields
        assert "baby_age" in context, "Baby age not extracted"
        assert context["baby_age"]["value"] == 4, "Incorrect age value"
        assert "travel_type" in context, "Travel type not extracted"
        assert context["travel_type"]["type"] == "flight", "Incorrect travel type"
        assert "duration" in context, "Duration not extracted"
        assert context["duration"]["value"] == 5, "Incorrect duration value"
        assert "destination_info" in context, "Destination info not extracted"
        
        logger.info("Travel agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Travel agent test failed: {str(e)}", exc_info=True)
        raise

async def run_all_tests():
    """Run all agent tests"""
    try:
        logger.info("Starting all agent tests")
        
        await test_budget_agent()
        await test_pregnancy_agent()
        await test_travel_agent()
        
        logger.info("All agent tests completed successfully")
        
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all_tests()) 