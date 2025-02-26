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
        
        thread_data = await get_or_create_memory(session_id)
        
        # Test case 1: Budget planning query
        message = "I need help planning a budget of $1500 per month for baby essentials and gear. We need a stroller urgently."
        logger.info(f"Test case 1 - Processing message: {message}")
        
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
        
        # Test case 2: Budget constraint query
        message = "What baby gear can I get within $500?"
        logger.info(f"Test case 2 - Processing message: {message}")
        
        result = await container.agent_factory.route_query(
            query=message,
            session_id=session_id
        )
        
        # Verify context is updated
        context = thread_data["state"]["gathered_info"]
        logger.info(f"Updated context: {context}")
        
        assert "budget_range" in context, "Budget range not extracted"
        assert context["budget_range"]["value"] == 500, "Incorrect budget value"
        
        # Test case 3: Monthly expense query
        message = "How should I allocate my monthly baby budget of $2000?"
        logger.info(f"Test case 3 - Processing message: {message}")
        
        result = await container.agent_factory.route_query(
            query=message,
            session_id=session_id
        )
        
        # Verify context is updated
        context = thread_data["state"]["gathered_info"]
        logger.info(f"Updated context: {context}")
        
        assert "budget_range" in context, "Budget range not extracted"
        assert context["budget_range"]["value"] == 2000, "Incorrect budget value"
        assert "timeframe" in context, "Timeframe not extracted"
        assert context["timeframe"]["period"] == "monthly", "Incorrect timeframe period"
        
        logger.info("Budget agent test completed successfully")
        
    except Exception as e:
        logger.error(f"Budget agent test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_budget_agent()) 