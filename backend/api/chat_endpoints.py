from fastapi import APIRouter, HTTPException
from fastapi.logger import logger
from backend.chat import chat
from backend.models import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Process a chat message and return a response"""
    try:
        logger.info(f"Received chat request for thread {request.thread_id}")
        
        # Call the chat function
        response = chat(
            thread_id=request.thread_id,
            message=request.message,
            language=request.language
        )
        
        logger.info(f"Generated response for thread {request.thread_id}")
        return response
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}") 