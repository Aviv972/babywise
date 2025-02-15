from fastapi import APIRouter, HTTPException, Response
from src.models.chat import ChatMessage, ChatResponse
from src.services.chat_session import ChatSession
from src.services.agent_factory import AgentFactory
from src.services.llm_service import LLMService
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import json

router = APIRouter()
llm_service = LLMService()
agent_factory = AgentFactory(llm_service)
chat_sessions = {}

@router.post("/chat")
async def chat(request: ChatMessage):
    try:
        if "manager" not in chat_sessions:
            print("Initializing new chat session...")
            chat_sessions["manager"] = ChatSession(agent_factory)
        
        print(f"Received message: {request.message}")
        response = await chat_sessions["manager"].process_query(request.message)
        print(f"\n=== Final Response Before Sending ===\nFormat: {json.dumps(response, indent=2)}")
        
        # Ensure response is in correct format
        formatted_response = {
            "type": response.get("type", "answer"),
            "text": response.get("text", str(response))
        }
        
        # Convert to JSON-safe format and return
        json_compatible = jsonable_encoder(formatted_response)
        return json_compatible

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return {
            "type": "error",
            "text": str(e)
        } 