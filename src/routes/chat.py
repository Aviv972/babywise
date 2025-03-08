from fastapi import APIRouter, HTTPException, Depends
from src.models.chat import ChatMessage, ChatResponse
from src.services.chat_session import ChatSession
from fastapi.responses import JSONResponse
from typing import Dict
from src.services.service_container import container
import logging
import asyncio
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Store chat sessions
chat_sessions: Dict[str, ChatSession] = {}

async def get_chat_session() -> ChatSession:
    """Get or create a chat session"""
    try:
        if "manager" not in chat_sessions:
            logger.info("Initializing new chat session...")
            if not container.agent_factory:
                logger.error("Agent factory not initialized!")
                raise RuntimeError("Chat service not properly initialized")
            session = ChatSession(container.agent_factory)
            await session.initialize()
            chat_sessions["manager"] = session
            logger.info("New chat session created successfully")
        return chat_sessions["manager"]
    except Exception as e:
        logger.error(f"Error in get_chat_session: {str(e)}", exc_info=True)
        raise

@router.post("/")
async def chat(
    request: ChatMessage,
    chat_session: ChatSession = Depends(get_chat_session)
) -> JSONResponse:
    """
    Process a chat message with context management
    """
    try:
        logger.info("\n=== Starting Chat Request Processing ===")
        start_time = datetime.utcnow()
        logger.info(f"Received message: {request.message}")
        
        # Process the query with context
        response = await chat_session.process_query(request.message)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Processing time: {processing_time} seconds")
        
        if not response:
            logger.warning("Empty response received from chat session")
            return JSONResponse(
                content={
                    "type": "error",
                    "text": "I apologize, but I couldn't generate a response. Could you please rephrase your question?",
                    "metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "role": "assistant"
                    }
                }
            )
        
        # Ensure response has proper WhatsApp format
        formatted_response = {
            "type": response.get("type", "answer"),
            "text": response.get("text", ""),
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "role": "assistant"
            }
        }
        
        # Add any additional fields from the original response
        if "field" in response:
            formatted_response["field"] = response["field"]
        if "products" in response:
            formatted_response["products"] = response["products"]
        
        logger.info(f"Response generated successfully - Type: {formatted_response['type']}")
        logger.info(f"Response text length: {len(formatted_response['text'])}")
        
        return JSONResponse(content=formatted_response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        error_type = type(e).__name__
        
        error_response = {
            "type": "error",
            "text": "I encountered an unexpected issue. Could you rephrase your question?",
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "role": "assistant",
                "error_type": error_type
            }
        }
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    finally:
        logger.info("=== Chat Request Processing Complete ===\n")

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