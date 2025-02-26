import pytest
import pytest_asyncio
from src.agents.general_agent import GeneralAgent
from src.services.chat_session import ChatSession
from src.services.agent_router import AgentRouter
from src.services.agent_factory import AgentFactory
from src.services.llm_service import LLMService
from src.config import get_settings
from src.langchain.config import BabywiseState
from langchain_core.messages import HumanMessage, AIMessage
from typing import List
from langchain_core.messages import BaseMessage

settings = get_settings()

class MockLLMService:
    """Mock LLM service for testing"""
    def __init__(self):
        pass

    async def agenerate_response(self, messages: List[BaseMessage], system_prompt=None, context=None) -> AIMessage:
        """Mock response generation"""
        # Get the last message content
        prompt = messages[-1].content if messages else ""
        
        # Return different responses based on the prompt
        if "Hi, I need help" in prompt:
            return AIMessage(content="Hello! I'm here to help you with your baby care needs.")
        elif "months old" in prompt:
            return AIMessage(content="I understand your baby is a few months old. Let me help you with age-appropriate advice.")
        elif "feed" in prompt:
            return AIMessage(content="Before I can provide feeding advice, I need to know your baby's age.")
        elif "sleeping well" in prompt:
            return AIMessage(content="I see multiple concerns about sleep, health, and feeding. Let me help you with each.")
        else:
            return AIMessage(content="How old is your baby?")

@pytest_asyncio.fixture
async def chat_session():
    """Create a test chat session"""
    session_id = "test_session"
    llm_service = MockLLMService()
    agent_factory = AgentFactory(llm_service)
    agent_router = AgentRouter(agent_factory, session_id)
    return ChatSession(session_id, agent_router)

@pytest.mark.asyncio
async def test_general_agent_basic_query(chat_session):
    """Test basic query handling by general agent"""
    # Test basic greeting
    response = await chat_session.process_message("Hi, I need help with my baby")
    assert response.type == "text"
    assert "help" in response.text.lower()
    assert response.metadata["agent_type"] == "general"

@pytest.mark.asyncio
async def test_general_agent_context_extraction(chat_session):
    """Test context extraction capabilities"""
    # Test age extraction
    response = await chat_session.process_message("My baby is 6 months old")
    assert response.metadata.get("metadata", {}).get("extracted_context", {}).get("baby_age") == {
        "value": 6,
        "unit": "months",
        "original": "6 months"
    }

@pytest.mark.asyncio
async def test_general_agent_followup(chat_session):
    """Test follow-up question handling"""
    # Initial query without context
    response = await chat_session.process_message("What should I feed my baby?")
    assert "age" in response.text.lower()  # Should ask for age
    
    # Provide age context
    response = await chat_session.process_message("She is 6 months old")
    assert "6 month" in response.metadata.get("metadata", {}).get("extracted_context", {}).get("baby_age", {}).get("original", "")

@pytest.mark.asyncio
async def test_general_agent_complex_query(chat_session):
    """Test handling of complex, multi-domain queries"""
    response = await chat_session.process_message(
        "My 8-month-old isn't sleeping well, has a slight fever, and isn't eating properly"
    )
    # Should identify multiple concerns and suggest appropriate specialist agents
    assert response.text  # Verify response exists
    assert any(word in response.text.lower() for word in ["sleep", "health", "feeding"])

@pytest.mark.asyncio
async def test_general_agent_context_persistence(chat_session):
    """Test if context is maintained across messages"""
    # Set initial context
    await chat_session.process_message("I have a 7-month-old baby")
    
    # Check if context is maintained in subsequent queries
    response = await chat_session.process_message("What activities are appropriate?")
    context = response.metadata.get("extracted_context", {})
    assert context.get("baby_age", {}).get("value") == 7

if __name__ == "__main__":
    pytest.main(["-v", "test_general_agent.py"]) 