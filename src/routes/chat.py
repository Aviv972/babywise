from fastapi import APIRouter, WebSocket, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Optional, Any, Mapping, List
from datetime import datetime
import logging
import json
from pydantic import BaseModel

# Try to import the container, but provide a fallback if it fails
try:
    from src.services.service_container import container
except ImportError:
    # Create a dummy container object
    class DummyContainer:
        def get_llm_service(self):
            return None
        def get_memory_service(self):
            return None
    container = DummyContainer()

from src.config import get_settings
from src.models.chat import ChatState, ChatMessage, ChatResponse, ChatHistory, ChatRequest
from src.langchain import (
    BabywiseState,
    get_context as get_thread_context,
    chat as process_chat,
    reset_thread
)
from langchain_core.messages import BaseMessage
from src.utils.memory_utils import (
    get_or_create_memory, 
    create_memory_components, 
    convert_from_langchain_messages,
    extract_context_from_messages
)

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# Store conversation instances with LangChain memory
conversations: Mapping[str, Dict[str, Any]] = {}

class ConversationState(BaseModel):
    """Enhanced conversation state with LangChain integration"""
    original_query: Optional[str] = None
    gathered_info: Dict[str, Any] = {}
    conversation_history: List[Dict[str, Any]] = []
    context_relevance: Dict[str, float] = {}
    agent_type: Optional[str] = None
    langchain_messages: Optional[List[BaseMessage]] = None
    memory_components: Optional[Dict[str, Any]] = None

class ConversationData(BaseModel):
    conversation_data: ConversationState

class ErrorResponse(BaseModel):
    type: str = "error"
    text: str
    metadata: Dict[str, Any]

class SuccessResponse(BaseModel):
    status: str = "success"
    message: str
    context: Optional[ConversationState] = None

async def get_or_create_memory(thread_id: str, db_url: str) -> Dict[str, Any]:
    """Get or create LangChain memory components for a thread"""
    if thread_id not in conversations:
        logger.info(f"Creating new memory components for thread {thread_id}")
        memory_components = create_memory_components(
            session_id=thread_id,
            db_url=db_url
        )
        conversations[thread_id] = {
            "memory": memory_components,
            "state": ChatState(
                messages=[],
                thread_id=thread_id
            ).dict()
        }
    return conversations[thread_id]

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message and return response"""
    try:
        # Get or create memory components for this thread
        thread_data = await get_or_create_memory(request.thread_id, container.db_url)
        
        # Route query through agent factory
        response = await container.agent_factory.route_query(
            query=request.message,
            session_id=request.thread_id
        )
        
        # Update state with messages from memory
        thread_data["state"]["messages"] = thread_data["memory"]["shared_memory"].chat_memory.messages
        
        return ChatResponse(
            text=response.get("text", ""),
            type=response.get("type", "text"),
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "thread_id": request.thread_id
            },
            messages=thread_data["state"]["messages"]
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request"
        )

@router.get("/context/{thread_id}", response_model=Dict[str, Any])
async def get_context(
    thread_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Get conversation context with LangChain memory"""
    try:
        thread_data = await get_or_create_memory(thread_id, container.db_url)
        messages = thread_data["memory"]["shared_memory"].chat_memory.messages
        
        if limit:
            messages = messages[-limit:]
        
        return {
            "messages": convert_from_langchain_messages(messages),
            "state": thread_data["state"],
            "context": extract_context_from_messages(messages)
        }
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset/{thread_id}", response_model=SuccessResponse)
async def reset_chat(thread_id: str) -> SuccessResponse:
    """Reset conversation with LangChain memory"""
    try:
        if thread_id in conversations:
            del conversations[thread_id]
        return SuccessResponse(message=f"Conversation thread {thread_id} reset successfully")
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint with LangChain memory support"""
    await websocket.accept()
    logger.info(f"WebSocket connection established for session {session_id}")
    
    try:
        # Get or create memory components
        thread_data = await get_or_create_memory(session_id, container.db_url)
        
        while True:
            # Receive message
            message = await websocket.receive_text()
            
            # Convert to LangChain format and update memory
            langchain_message = ChatMessage(
                message=message,
                session_id=session_id,
                metadata={"role": "user"}
            ).to_langchain()
            
            thread_data["memory"]["shared_memory"].chat_memory.add_message(langchain_message)
            thread_data["state"]["messages"].append(langchain_message)
            
            # Route to appropriate agent and get response
            result = await container.agent_factory.route_query(
                query=message,
                session_id=session_id
            )
            
            # Convert response to LangChain format and update memory
            assistant_message = ChatMessage(
                message=result["text"],
                session_id=session_id,
                metadata={"role": "assistant"}
            ).to_langchain()
            
            thread_data["memory"]["shared_memory"].chat_memory.add_message(assistant_message)
            thread_data["state"]["messages"].append(assistant_message)
            
            # Send response
            await websocket.send_text(result["text"])
            
    except Exception as e:
        logger.error(f"Error in websocket connection: {str(e)}", exc_info=True)
        await websocket.close()

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        # Create a temporary agent to access the history
        agent = container.agent_factory.create_agent(
            agent_type="general",
            session_id=session_id
        )
        
        # Get messages from the memory
        messages = agent.memory.chat_memory.messages
        
        # Format messages for response
        history = [
            {
                "role": "user" if msg.type == "human" else "assistant",
                "content": msg.content,
                "timestamp": msg.additional_kwargs.get("timestamp", "")
            }
            for msg in messages
        ]
        
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving chat history"
        ) 