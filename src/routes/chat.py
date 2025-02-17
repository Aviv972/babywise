from fastapi import APIRouter, HTTPException, Depends
from src.models.chat import ChatMessage, ChatResponse
from src.services.chat_session import ChatSession
from fastapi.responses import JSONResponse
from typing import Dict
from src.services.service_container import container

router = APIRouter()

# Store chat sessions
chat_sessions: Dict[str, ChatSession] = {}

async def get_chat_session() -> ChatSession:
    """Get or create a chat session"""
    if "manager" not in chat_sessions:
        print("Initializing new chat session...")
        chat_sessions["manager"] = ChatSession(container.agent_factory)
    return chat_sessions["manager"]

@router.post("/")
async def chat(
    request: ChatMessage,
    chat_session: ChatSession = Depends(get_chat_session)
) -> JSONResponse:
    """
    Process a chat message with context management
    """
    try:
        print(f"\n=== Received Message ===\n{request.message}")
        
        # Process the query with context
        response = await chat_session.process_query(request.message)
        
        print(f"\n=== Final Response ===\n{response}")
        
        # Return JSON response
        return JSONResponse(content={
            "type": response.get("type", "answer"),
            "text": response.get("text", str(response))
        })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "text": str(e)
            }
        )

@router.get("/context")
async def get_context(
    chat_session: ChatSession = Depends(get_chat_session)
) -> JSONResponse:
    """
    Get the current conversation context
    """
    try:
        return JSONResponse(content=chat_session.get_state())
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "text": str(e)
            }
        )

@router.post("/reset")
async def reset_chat(
    chat_session: ChatSession = Depends(get_chat_session)
) -> JSONResponse:
    """
    Reset the chat session
    """
    try:
        chat_session.reset()
        return JSONResponse(content={
            "status": "success",
            "message": "Chat session reset successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "text": str(e)
            }
        ) 