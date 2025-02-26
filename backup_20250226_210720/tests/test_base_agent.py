import pytest
from src.agents.base_agent import BaseAgent
from src.constants import ResponseTypes
import logging

# Test implementation of BaseAgent
class TestAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = "TEST"
        self.name = "Test Agent"
        self.expertise = ["test"]
        self.required_context = ["test_field"]

    async def _process_agent_specific(self, query: str, context: dict, chat_history: list) -> dict:
        return {
            'type': ResponseTypes.ANSWER,
            'text': "Test response",
            'context': context
        }

# Mock LLM service
class MockLLMService:
    async def generate_response(self, *args, **kwargs):
        return {"text": "Mock response"}

@pytest.fixture
def agent():
    return TestAgent(MockLLMService())

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test agent initialization"""
    assert agent.agent_type == "TEST"
    assert agent.name == "Test Agent"
    assert agent.expertise == ["test"]
    assert agent.required_context == ["test_field"]

@pytest.mark.asyncio
async def test_emergency_detection(agent):
    """Test emergency situation detection"""
    emergency_query = "My baby is choking!"
    normal_query = "What's a good bedtime routine?"
    
    assert agent._is_emergency_situation(emergency_query) == True
    assert agent._is_emergency_situation(normal_query) == False

@pytest.mark.asyncio
async def test_medical_disclaimer(agent):
    """Test medical disclaimer addition"""
    medical_query = "My baby has a fever"
    normal_query = "What stroller do you recommend?"
    
    assert agent._needs_medical_disclaimer(medical_query) == True
    assert agent._needs_medical_disclaimer(normal_query) == False

@pytest.mark.asyncio
async def test_missing_fields_detection(agent):
    """Test detection of missing required fields"""
    context_complete = {"gathered_info": {"test_field": "value"}}
    context_incomplete = {"gathered_info": {}}
    
    missing_fields = agent._get_missing_critical_fields(context_incomplete)
    assert "test_field" in missing_fields
    
    missing_fields = agent._get_missing_critical_fields(context_complete)
    assert len(missing_fields) == 0

@pytest.mark.asyncio
async def test_query_processing(agent):
    """Test basic query processing"""
    query = "Test query"
    context = {"gathered_info": {"test_field": "value"}}
    
    response = await agent.process_query(query, context)
    assert response["type"] == ResponseTypes.ANSWER
    assert "text" in response
    assert "context" in response

@pytest.mark.asyncio
async def test_emergency_response(agent):
    """Test emergency response generation"""
    query = "My baby is choking!"
    response = await agent.process_query(query)
    
    assert response["type"] == ResponseTypes.EMERGENCY
    assert "911" in response["text"]
    assert "emergency services" in response["text"].lower()

@pytest.mark.asyncio
async def test_error_handling(agent, caplog):
    """Test error handling during query processing"""
    # Force an error by passing invalid context
    with caplog.at_level(logging.ERROR):
        response = await agent.process_query("test", context=None)
        
    assert response["type"] == ResponseTypes.ERROR
    assert "rephrase" in response["text"].lower()
    assert len(caplog.records) > 0  # Ensure error was logged 