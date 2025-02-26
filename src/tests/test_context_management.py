import pytest
from unittest.mock import Mock, AsyncMock
from src.services.chat_session import ChatSession
from src.services.agent_factory import AgentFactory
from src.constants import MessageRoles, ResponseTypes, QuestionFields
from src.services.llm_service import LLMService

class MockAgent:
    async def process_query(self, query, context, chat_history):
        query_lower = query.lower()
        
        # Handle stroller queries
        if "stroller" in query_lower or "עגלה" in query_lower:
            return {
                "type": "text",
                "text": "Let me help you find a stroller. I'll need some information.",
                "addressed_fields": ["stroller_type"],
                "previous_field": "stroller_type"
            }
            
        # Handle age information
        if "month" in query_lower or "year" in query_lower:
            return {
                "type": "text",
                "text": "Noted the age information",
                "addressed_fields": ["baby_age"],
                "previous_field": "baby_age"
            }
            
        # Handle location/usage information
        if "urban" in query_lower or "city" in query_lower:
            return {
                "type": "text",
                "text": "Noted the usage environment",
                "addressed_fields": ["usage"],
                "previous_field": "usage"
            }
            
        # Default response
        return {
            "type": "text",
            "text": "Here is your final recommendation",
            "addressed_fields": [],
            "previous_field": None
        }

class MockLLMService:
    async def generate_response(self, *args, **kwargs):
        return "Mock response"
        
    async def analyze_query_intent(self, *args, **kwargs):
        return {"intent": "mock_intent"}

@pytest.fixture
def mock_llm_service():
    return MockLLMService()

@pytest.fixture
def mock_agent():
    return MockAgent()

@pytest.fixture
def chat_session(mock_llm_service):
    agent_factory = AgentFactory(mock_llm_service)
    # Mock the get_agent_for_query method
    agent_factory.get_agent_for_query = AsyncMock(return_value=MockAgent())
    return ChatSession(agent_factory)

@pytest.mark.asyncio
async def test_context_retention_and_relevance(chat_session):
    # Initial query about stroller
    response = await chat_session.process_query("I need a stroller for my 6 month old baby")
    
    # Verify initial context setup
    context = chat_session.get_state()
    assert context['original_query'] == "I need a stroller for my 6 month old baby"
    assert context['agent_type'] == 'baby_gear'
    
    # Add budget information
    response = await chat_session.process_query("My budget is $300")
    
    # Verify budget was captured and scored for relevance
    context = chat_session.get_state()
    assert context['gathered_info'].get(QuestionFields.BUDGET) == "$300"
    assert context['context_relevance'].get(QuestionFields.BUDGET, 0) > 0.3
    
    # Switch topic briefly
    response = await chat_session.process_query("How many hours should a 6 month old sleep?")
    
    # Return to stroller topic
    response = await chat_session.process_query("I prefer a lightweight stroller")
    
    # Verify original context was maintained
    context = chat_session.get_state()
    assert context['gathered_info'].get(QuestionFields.BUDGET) == "$300"  # Budget info retained
    assert 'lightweight' in str(context['conversation_history']).lower()  # New preference recorded

@pytest.mark.asyncio
async def test_smart_history_filtering(chat_session):
    # Create a sequence of messages
    queries = [
        "I need a stroller",
        "My budget is $300",
        "It needs to be lightweight",
        "How many hours should a baby sleep?",  # Irrelevant query
        "Does the stroller fold easily?"  # Back to relevant topic
    ]
    
    for query in queries:
        await chat_session.process_query(query)
    
    # Get filtered history
    history = chat_session.context.get_recent_history(limit=3)
    
    # Verify most relevant messages are retained
    history_content = [msg['content'] for msg in history]
    assert any('stroller' in content.lower() for content in history_content)
    assert any('$300' in content for content in history_content)
    assert any('fold' in content.lower() for content in history_content)

@pytest.mark.asyncio
async def test_field_relationship_tracking(chat_session):
    # Start with stroller query
    await chat_session.process_query("I need a stroller for my baby")
    
    # Add related information
    await chat_session.process_query("My baby is 6 months old")
    await chat_session.process_query("I need it for daily walks")
    
    # Verify field relationships
    context = chat_session.get_state()
    
    # Check that age information was captured
    assert context['gathered_info'].get(QuestionFields.BABY_AGE) == "6 months"
    
    # Check that usage information was linked to stroller context
    assert any(
        'daily walks' in str(msg).lower() 
        for msg in context['conversation_history']
    )
    
    # Verify metadata tracking
    last_message = context['conversation_history'][-1]
    assert 'metadata' in last_message
    assert 'identified_topics' in last_message['metadata']
    assert 'timestamp' in last_message['metadata']

@pytest.mark.asyncio
async def test_relevance_scoring(chat_session):
    # Initial stroller query
    await chat_session.process_query("I need a stroller that's good for travel")
    
    # Add relevant information
    await chat_session.process_query("My budget is $300")
    await chat_session.process_query("I travel frequently by airplane")
    
    # Add less relevant information
    await chat_session.process_query("What's a good bedtime routine?")
    
    # Get context with relevance scores
    context = chat_session.get_state()
    
    # Check relevance scores
    relevance_scores = context['context_relevance']
    
    # Travel-related content should have high relevance
    assert any(
        score > 0.5 
        for field, score in relevance_scores.items() 
        if 'travel' in str(field).lower()
    )
    
    # Sleep-related content should have lower relevance
    assert all(
        score < 0.5 
        for field, score in relevance_scores.items() 
        if 'sleep' in str(field).lower()
    ) 