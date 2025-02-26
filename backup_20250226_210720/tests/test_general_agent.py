import asyncio
import pytest
from src.services.service_container import container
from src.utils.memory_utils import get_or_create_memory
from src.config import get_settings
from src.constants import AgentTypes
from tests.mock_llm_service import MockLLMService
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def mock_llm_context():
    """Context manager for mock LLM service"""
    original_llm = container.llm_service
    try:
        container.llm_service = MockLLMService()
        yield container
    finally:
        container.llm_service = original_llm

@pytest.fixture
async def mock_container():
    """Create a container with mock services for testing"""
    # Store original LLM service
    original_llm = container.llm_service
    
    try:
        # Replace with mock service
        container.llm_service = MockLLMService()
        yield container
    finally:
        # Restore original service
        container.llm_service = original_llm

@pytest.mark.asyncio
async def test_general_agent_routing():
    """Test the GeneralAgent's ability to handle and route different types of queries"""
    try:
        # Initialize test session
        session_id = "test_general_session"
        logger.info(f"Starting general agent test with session_id: {session_id}")
        
        # Get memory components for the session
        thread_data = await get_or_create_memory(session_id)
        
        # Test Case 1: Initial general query
        message1 = "I have a 6-month-old baby and I'm looking for general advice on daily routines"
        logger.info(f"Test Case 1 - Processing message: {message1}")
        
        result1 = await container.agent_factory.route_query(
            query=message1,
            session_id=session_id
        )
        
        # Verify agent selection and context extraction
        assert result1["type"] == "answer", "Expected answer type response"
        context1 = thread_data["state"]["gathered_info"]
        assert "baby_age" in context1, "Baby age not extracted"
        assert context1["baby_age"]["value"] == 6, "Incorrect baby age"
        
        # Test Case 2: Follow-up query with context
        message2 = "What kind of schedule should I follow?"
        logger.info(f"Test Case 2 - Processing follow-up message: {message2}")
        
        result2 = await container.agent_factory.route_query(
            query=message2,
            session_id=session_id
        )
        
        # Verify context persistence
        context2 = thread_data["state"]["gathered_info"]
        assert "baby_age" in context2, "Context not persisted"
        assert context2["baby_age"]["value"] == 6, "Context value changed"
        
        # Test Case 3: Sleep-specific query (should trigger agent switch)
        message3 = "My baby is having trouble sleeping through the night"
        logger.info(f"Test Case 3 - Processing sleep-related message: {message3}")
        
        result3 = await container.agent_factory.route_query(
            query=message3,
            session_id=session_id
        )
        
        # Verify agent switching
        current_agent = await container.agent_factory.get_agent_for_query(message3, session_id=session_id)
        assert current_agent.agent_type == AgentTypes.SLEEP, "Failed to switch to sleep agent"
        
        # Test Case 4: Return to general query
        message4 = "Can you give me general tips for baby care?"
        logger.info(f"Test Case 4 - Processing general message: {message4}")
        
        result4 = await container.agent_factory.route_query(
            query=message4,
            session_id=session_id
        )
        
        # Verify return to general agent
        final_agent = await container.agent_factory.get_agent_for_query(message4, session_id=session_id)
        assert final_agent.agent_type == AgentTypes.GENERAL, "Failed to return to general agent"
        
        # Test Case 5: Complex query requiring multiple agents
        message5 = "My baby isn't sleeping well and seems to be teething. What should I do?"
        logger.info(f"Test Case 5 - Processing complex message: {message5}")
        
        result5 = await container.agent_factory.route_query(
            query=message5,
            session_id=session_id
        )
        
        # Verify handling of complex query
        assert result5["type"] == "answer", "Failed to handle complex query"
        
        logger.info("General agent test completed successfully")
        
    except Exception as e:
        logger.error(f"General agent test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_context_persistence():
    """Test the GeneralAgent's ability to maintain and use context across interactions"""
    try:
        async with mock_llm_context() as mock_container:
            # Initialize test session
            session_id = "test_context_session"
            logger.info(f"Starting context persistence test with session_id: {session_id}")
            
            # Get memory components for the session
            thread_data = await get_or_create_memory(session_id)
            
            # Test Case 1: Initial context setting
            message1 = "I have a 4-month-old baby who is exclusively breastfed"
            logger.info(f"Test Case 1 - Setting initial context: {message1}")
            
            result1 = await mock_container.agent_factory.route_query(
                query=message1,
                session_id=session_id
            )
            
            # Verify initial context extraction
            context1 = thread_data["state"]["gathered_info"]
            assert "baby_age" in context1, "Baby age not extracted"
            assert context1["baby_age"]["value"] == 4, "Incorrect baby age"
            assert "feeding_type" in context1, "Feeding type not extracted"
            
            # Test Case 2: Context maintenance
            message2 = "What kind of schedule should we follow?"
            logger.info(f"Test Case 2 - Testing context maintenance: {message2}")
            
            result2 = await mock_container.agent_factory.route_query(
                query=message2,
                session_id=session_id
            )
            
            # Verify context persistence
            context2 = thread_data["state"]["gathered_info"]
            assert "baby_age" in context2, "Context not maintained"
            assert context2["baby_age"]["value"] == 4, "Context value changed"
            assert "feeding_type" in context2, "Feeding context lost"
            
            # Test Case 3: Context enhancement
            message3 = "We follow attachment parenting style and co-sleep"
            logger.info(f"Test Case 3 - Enhancing context: {message3}")
            
            result3 = await mock_container.agent_factory.route_query(
                query=message3,
                session_id=session_id
            )
            
            # Verify context enhancement
            context3 = thread_data["state"]["gathered_info"]
            assert "parenting_style" in context3, "New context not added"
            assert "baby_age" in context3, "Previous context lost"
            assert context3["baby_age"]["value"] == 4, "Previous context changed"
            
            # Test Case 4: Context usage in responses
            message4 = "What activities are appropriate for us?"
            logger.info(f"Test Case 4 - Testing context usage: {message4}")
            
            result4 = await mock_container.agent_factory.route_query(
                query=message4,
                session_id=session_id
            )
            
            # Verify context-aware response
            response_text = result4["text"].lower()
            assert "4 month" in response_text or "4-month" in response_text, "Age context not used in response"
            assert "attachment" in response_text, "Parenting style context not used in response"
            
            logger.info("Context persistence test completed successfully")
            
    except Exception as e:
        logger.error(f"Context persistence test failed: {str(e)}", exc_info=True)
        raise

@pytest.mark.asyncio
async def test_agent_switching():
    """Test the system's ability to switch between agents appropriately"""
    try:
        session_id = "test_switching_session"
        logger.info(f"Starting agent switching test with session_id: {session_id}")
        
        thread_data = await get_or_create_memory(session_id)
        
        # Test Case 1: Start with general query
        message1 = "I have a 4-month-old baby"
        logger.info(f"Test Case 1 - Starting with general query: {message1}")
        
        result1 = await container.agent_factory.route_query(
            query=message1,
            session_id=session_id
        )
        
        agent1 = await container.agent_factory.get_agent_for_query(message1, session_id=session_id)
        assert agent1.agent_type == AgentTypes.GENERAL, "Should start with general agent"
        
        # Test Case 2: Switch to sleep agent
        message2 = "She's waking up every 2 hours at night"
        logger.info(f"Test Case 2 - Sleep-related query: {message2}")
        
        result2 = await container.agent_factory.route_query(
            query=message2,
            session_id=session_id
        )
        
        agent2 = await container.agent_factory.get_agent_for_query(message2, session_id=session_id)
        assert agent2.agent_type == AgentTypes.SLEEP, "Should switch to sleep agent"
        
        # Test Case 3: Switch to health agent
        message3 = "And she has a slight fever"
        logger.info(f"Test Case 3 - Health-related query: {message3}")
        
        result3 = await container.agent_factory.route_query(
            query=message3,
            session_id=session_id
        )
        
        agent3 = await container.agent_factory.get_agent_for_query(message3, session_id=session_id)
        assert agent3.agent_type == AgentTypes.HEALTH, "Should switch to health agent"
        
        # Test Case 4: Complex query requiring coordination
        message4 = "Could the fever be affecting her sleep?"
        logger.info(f"Test Case 4 - Complex multi-domain query: {message4}")
        
        result4 = await container.agent_factory.route_query(
            query=message4,
            session_id=session_id
        )
        
        # Verify handling of complex query
        assert result4["type"] == "answer", "Failed to handle complex query"
        assert "sleep" in result4["text"].lower() and "fever" in result4["text"].lower(), "Response should address both sleep and health"
        
        logger.info("Agent switching test completed successfully")
        
    except Exception as e:
        logger.error(f"Agent switching test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Run all tests
    asyncio.run(test_general_agent_routing())
    asyncio.run(test_context_persistence())
    asyncio.run(test_agent_switching()) 