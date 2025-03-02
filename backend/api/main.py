"""
Babywise Chatbot - Main API

This module implements the main FastAPI application for the Babywise Chatbot,
including chat endpoints and routine tracker functionality.
"""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import pathlib

# Load environment variables from .env file
# Try multiple possible locations for the .env file
possible_paths = [
    pathlib.Path(__file__).parents[2] / '.env',  # Original path
    pathlib.Path(__file__).parents[1] / '.env',  # One level up
    pathlib.Path.cwd() / '.env',                 # Current working directory
]

for dotenv_path in possible_paths:
    if dotenv_path.exists():
        print(f"Found .env file at: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
        if 'OPENAI_API_KEY' in os.environ and os.environ['OPENAI_API_KEY']:
            print(f"Successfully loaded OpenAI API key from {dotenv_path}")
            break

# Verify OpenAI API key is loaded
if 'OPENAI_API_KEY' not in os.environ or not os.environ['OPENAI_API_KEY']:
    logging.warning("OPENAI_API_KEY not found or empty in environment variables. Mock responses will be used.")

from backend.services.chat_service import process_chat, get_thread_context, reset_thread_state
from backend.api.routine_endpoints import router as routine_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Babywise Chatbot API",
    description="API for the Babywise Chatbot, providing baby care advice and routine tracking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    language: str = Field("en", description="Language code (e.g., 'en', 'he', 'ar')")

class ChatResponse(BaseModel):
    text: str = Field(..., description="Assistant response")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")
    domain: str = Field(..., description="Detected domain of the conversation")
    context: Dict[str, Any] = Field({}, description="Extracted context from the conversation")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")

# Include routine tracker endpoints
app.include_router(routine_router)

# Chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    """Process a chat message and return a response"""
    try:
        # Generate a thread ID if not provided
        thread_id = request.thread_id or os.urandom(16).hex()
        
        # Process the message
        result = await process_chat(
            thread_id=thread_id,
            message=request.message,
            language=request.language
        )
        
        # Return the response
        return {
            "text": result["text"],
            "thread_id": thread_id,
            "domain": result["domain"],
            "context": result["context"],
            "metadata": result["metadata"]
        }
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

# Get context endpoint
@app.get("/context/{thread_id}")
async def handle_get_context(thread_id: str):
    """Get the current context for a thread"""
    try:
        result = get_thread_context(thread_id)
        return result
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting context: {str(e)}")

# Reset thread endpoint
@app.post("/reset/{thread_id}")
async def handle_reset_thread(thread_id: str):
    """Reset a thread's state"""
    try:
        result = reset_thread_state(thread_id)
        return result
    except Exception as e:
        logger.error(f"Error resetting thread: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error resetting thread: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Root path - serve a simple HTML page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root path - serve a simple HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Babywise Chatbot API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            h2 {
                color: #3498db;
                margin-top: 30px;
            }
            .endpoint {
                background-color: #f8f9fa;
                border-left: 4px solid #3498db;
                padding: 10px 15px;
                margin: 15px 0;
            }
            code {
                background-color: #f1f1f1;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <h1>Babywise Chatbot API</h1>
        <p>Welcome to the Babywise Chatbot API. This service provides baby care advice and routine tracking functionality.</p>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <h3>POST /chat</h3>
            <p>Send a message to the chatbot and receive a response.</p>
            <p>Example request:</p>
            <code>
                curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Hello, my baby is 3 months old", "thread_id": "test123"}'
            </code>
        </div>
        
        <div class="endpoint">
            <h3>POST /reset</h3>
            <p>Reset a conversation thread.</p>
            <p>Example request:</p>
            <code>
                curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{"thread_id": "test123"}'
            </code>
        </div>
        
        <div class="endpoint">
            <h3>GET /context/{thread_id}</h3>
            <p>Get the current context for a thread.</p>
            <p>Example request:</p>
            <code>
                curl http://localhost:8000/context/test123
            </code>
        </div>
        
        <div class="endpoint">
            <h3>GET /health</h3>
            <p>Health check endpoint.</p>
            <p>Example request:</p>
            <code>
                curl http://localhost:8000/health
            </code>
        </div>
        
        <h2>API Status</h2>
        <p>The API is currently running and ready to accept requests.</p>
    </body>
    </html>
    """
    return html_content

# Add debug endpoint for command detection
@app.post("/debug/detect-command")
async def debug_detect_command(request: ChatRequest):
    """Debug endpoint to test command detection"""
    try:
        from backend.workflow.command_parser import detect_command
        
        # Detect command
        command = detect_command(request.message)
        
        if command:
            return {
                "command_detected": True,
                "command": command,
                "message": request.message
            }
        else:
            return {
                "command_detected": False,
                "message": request.message
            }
    except Exception as e:
        logger.error(f"Error in debug command detection: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "message": request.message
        }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 