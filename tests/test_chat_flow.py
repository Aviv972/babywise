import pytest
from src.services.chat_session import ChatSession
from src.services.agent_factory import AgentFactory
from src.services.llm_service import LLMService

@pytest.fixture
def chat_session():
    llm_service = LLMService()
    agent_factory = AgentFactory(llm_service)
    return ChatSession(agent_factory)

@pytest.mark.asyncio
async def test_stroller_query_flow(chat_session):
    # Initial query
    response = await chat_session.process_message("מה העגלה הכי טובה לתינוק שלי?")
    
    # Should get age question first
    assert isinstance(response, dict)
    assert response['type'] == 'follow_up_question'
    assert 'age' in response['field']
    
    # Answer age question
    response = await chat_session.process_message("3 months")
    
    # Should get location question
    assert isinstance(response, dict)
    assert response['type'] == 'follow_up_question'
    assert 'location' in response['field']
    
    # Answer location
    response = await chat_session.process_message("urban")
    
    # Should get car type question
    assert isinstance(response, dict)
    assert response['type'] == 'follow_up_question'
    assert 'car_type' in response['field']
    
    # Answer car type
    response = await chat_session.process_message("SUV")
    
    # Should get living situation question
    assert isinstance(response, dict)
    assert response['type'] == 'follow_up_question'
    assert 'living_situation' in response['field']
    
    # Answer living situation
    response = await chat_session.process_message("apartment with elevator")
    
    # Should get budget question
    assert isinstance(response, dict)
    assert response['type'] == 'follow_up_question'
    assert 'budget_range' in response['field']
    
    # Answer budget
    response = await chat_session.process_message("2000-3000 שקל")
    
    # Should get final response
    assert isinstance(response, str)
    assert len(response) > 0
    
    # Check if context was stored
    context = chat_session.get_gathered_context()
    assert len(context) == 6  # Should have all 6 pieces of context
    assert context['age'] == ['3 months']
    assert context['budget_range'] == ['2000-3000 שקל']

@pytest.mark.asyncio
async def test_direct_query_flow(chat_session):
    """Test that specific queries still get context questions"""
    response = await chat_session.process_message("האם העגלה של Bugaboo טובה?")
    
    # Should still ask for context
    assert isinstance(response, dict)
    assert response['type'] == 'follow_up_question'

@pytest.mark.asyncio
async def test_context_persistence(chat_session):
    """Test that context is maintained between queries"""
    # First query with context gathering
    response = await chat_session.process_message("מה העגלה הכי טובה?")
    response = await chat_session.process_message("3 months")  # age
    response = await chat_session.process_message("urban")     # location
    
    # New related query should use existing context
    response = await chat_session.process_message("מה לגבי עגלת מקלארן?")
    assert isinstance(response, str)  # Should use existing context 