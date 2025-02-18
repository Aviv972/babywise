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
            chat_sessions["manager"] = ChatSession(container.agent_factory)
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
        # This ensures we maintain the core app logic for all messages
        response = await chat_session.process_query(request.message)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Processing time: {processing_time} seconds")
        
        if not response:
            logger.warning("Empty response received from chat session")
            return JSONResponse(
                content={
                    "type": "error",
                    "text": "I apologize, but I couldn't generate a response. Could you please rephrase your question?"
                }
            )
        
        if not isinstance(response, dict) or 'text' not in response:
            logger.warning(f"Invalid response format received: {response}")
            return JSONResponse(
                content={
                    "type": "error",
                    "text": "I encountered an issue processing your request. Could you please provide more details?"
                }
            )
        
        logger.info(f"Response generated successfully - Type: {response.get('type', 'unknown')}")
        logger.info(f"Response text length: {len(response.get('text', ''))}")
        
        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        error_type = type(e).__name__
        
        if 'API' in error_type:
            error_message = "I'm having trouble accessing external services. Please try again in a moment."
        elif 'Context' in error_type:
            error_message = "I need some more information to help you. Could you provide more details?"
        else:
            error_message = "I encountered an unexpected issue. Could you rephrase your question?"
        
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "text": error_message
            }
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