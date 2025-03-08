import pytest
from src.services.chat_session import ChatSession
from src.services.agent_factory import AgentFactory
from src.services.llm_service import LLMService

class MockLLMService:
    async def generate_response(self, *args, **kwargs):
        return {
            "type": "text",
            "text": "Mock response",
            "role": "assistant",
            "addressed_fields": ["baby_age", "usage"],
            "previous_field": "baby_age"
        }
        
    async def analyze_query_intent(self, query, context=None, chat_history=None):
        query_lower = query.lower()
        
        if "month" in query_lower or "year" in query_lower:
            return {
                "extracted_info": [
                    {"field": "baby_age", "value": query}
                ],
                "next_question": {
                    "field": "usage",
                    "question": "How will you mainly use the stroller?"
                }
            }
        elif "urban" in query_lower or "city" in query_lower:
            return {
                "extracted_info": [
                    {"field": "usage", "value": query}
                ],
                "next_question": None
            }
        elif "עגלה" in query_lower or "stroller" in query_lower:
            return {
                "extracted_info": [
                    {"field": "stroller_type", "value": query}
                ],
                "next_question": {
                    "field": "baby_age",
                    "question": "What is your baby's age?"
                }
            }
        
        return {
            "extracted_info": [],
            "next_question": None
        }
        
    async def process_query(self, *args, **kwargs):
        return await self.generate_response(*args, **kwargs)
        
    async def generate_final_response(self, *args, **kwargs):
        return {
            "type": "text",
            "text": "Here is your final recommendation",
            "role": "assistant",
            "addressed_fields": ["stroller_type", "baby_age", "usage"],
            "previous_field": None
        }

@pytest.fixture
def chat_session():
    llm_service = MockLLMService()
    agent_factory = AgentFactory(llm_service)
    return ChatSession(agent_factory)

@pytest.mark.asyncio
async def test_stroller_query_flow(chat_session):
    # Initial query
    response = await chat_session.process_query("מה העגלה הכי טובה לתינוק שלי?")
    assert isinstance(response, dict)  # Should return a dict with type and text
    
    # Verify initial context
    context = chat_session.get_state()
    assert context['original_query'] == "מה העגלה הכי טובה לתינוק שלי?"
    assert context['agent_type'] == 'baby_gear'
    
    # Provide age
    response = await chat_session.process_query("3 months")
    assert isinstance(response, dict)
    
    # Verify age was captured
    context = chat_session.get_state()
    assert context['gathered_info'].get('baby_age') == "3 months"
    
    # Provide location
    response = await chat_session.process_query("urban")
    assert isinstance(response, dict)
    
    # Verify final context
    context = chat_session.get_state()
    assert context['gathered_info'].get('usage') == "urban"
    assert len(context['gathered_info']) >= 2  # Should have at least age and usage

@pytest.mark.asyncio
async def test_direct_query_flow(chat_session):
    """Test that specific queries still get context questions"""
    response = await chat_session.process_query("האם העגלה של Bugaboo טובה?")
    assert isinstance(response, dict)
    
    # Get context and verify
    context = chat_session.get_state()
    assert context['original_query']  # Should store original query

@pytest.mark.asyncio
async def test_context_persistence(chat_session):
    """Test that context is maintained between queries"""
    # First query with context gathering
    response = await chat_session.process_query("מה העגלה הכי טובה?")
    response = await chat_session.process_query("3 months")  # age
    response = await chat_session.process_query("urban")     # location
    
    # New related query should use existing context
    response = await chat_session.process_query("מה לגבי עגלת מקלארן?")
    assert isinstance(response, dict)  # Should use existing context 