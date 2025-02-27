"""
Simplified FastAPI server for Babywise Chatbot.
This server relies on the LangGraph workflow for context retention.
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from pydantic import BaseModel

from src.langchain.simplified_workflow import chat, get_context, reset_thread

# Try to import the logging config, but don't fail if it's not available
try:
    from src.config.logging_config import setup_logging
    has_logging_config = True
except ImportError:
    has_logging_config = False
    print("Warning: Could not import logging_config. Using basic logging configuration.")

# Configure logging - VERCEL COMPATIBLE VERSION
# Check if we're in a read-only environment (like Vercel)
is_read_only = True
try:
    test_file_path = os.path.join(os.getcwd(), '.write_test')
    with open(test_file_path, 'w') as f:
        f.write('test')
    os.remove(test_file_path)
except (OSError, IOError):
    is_read_only = True
    print("Detected read-only filesystem. File logging disabled.")

# Configure basic logging with only console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # IMPORTANT: No FileHandler for Vercel compatibility
    ]
)
logger = logging.getLogger(__name__)

# Initialize logging using the config module if available
if has_logging_config:
    try:
        setup_logging()
        logger.info("Advanced logging configuration loaded")
    except Exception as e:
        logger.warning(f"Could not load advanced logging configuration: {str(e)}")
        logger.info("Using basic console logging only")
else:
    logger.info("Advanced logging configuration not available. Using basic console logging only.")

# Request logging middleware
class LoggingMiddleware:
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        start_time = datetime.now()
        path = scope["path"]
        method = scope.get("method", "")
        
        logger.info(f"Request started: {method} {path}")
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Request completed: {method} {path} - Status: {status_code} - Time: {process_time:.3f}s")
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

# Initialize FastAPI app with middleware
middleware = [
    Middleware(CORSMiddleware, 
               allow_origins=["*"], 
               allow_credentials=True, 
               allow_methods=["*"], 
               allow_headers=["*"])
]

app = FastAPI(
    title="Babywise Chatbot",
    description="A chatbot for baby care advice",
    version="0.1.0",
    middleware=middleware
)

# Add logging middleware manually
app.add_middleware(LoggingMiddleware)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    thread_id: str
    language: Optional[str] = "en"

class ChatResponse(BaseModel):
    text: str
    domain: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# API routes
@app.post("/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """Process a chat message and return a response"""
    try:
        logger.info(f"Processing message for thread {request.thread_id}: {request.message}")
        
        # Process the message
        response = await chat(request.message, request.thread_id, request.language)
        
        logger.info(f"Generated response for thread {request.thread_id}")
        logger.debug(f"Response context: {json.dumps(response.get('context', {}), default=str)}")
        
        return response
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}", exc_info=True)
        
        # Default error message
        error_message = "I apologize, but I encountered an error. Please try again."
        
        # Localized error messages
        if request.language == "es":
            error_message = "Lo siento, encontré un error. Por favor, inténtalo de nuevo."
        elif request.language == "fr":
            error_message = "Je m'excuse, mais j'ai rencontré une erreur. Veuillez réessayer."
        elif request.language == "de":
            error_message = "Ich entschuldige mich, aber ich bin auf einen Fehler gestoßen. Bitte versuchen Sie es erneut."
        elif request.language == "he":
            error_message = "אני מתנצל, אבל נתקלתי בשגיאה. אנא נסה שוב."
        elif request.language == "ar":
            error_message = "أعتذر، لكنني واجهت خطأ. يرجى المحاولة مرة أخرى."
        
        return {
            "text": error_message,
            "error": str(e),
            "language": request.language
        }

@app.get("/context/{thread_id}")
async def get_thread_context(thread_id: str):
    """Get the current context for a thread"""
    try:
        logger.info(f"Getting context for thread {thread_id}")
        context_data = get_context(thread_id)
        return context_data
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}", exc_info=True)
        return {
            "error": str(e)
        }

@app.post("/reset/{thread_id}")
async def reset_chat_thread(thread_id: str):
    """Reset a thread's state"""
    try:
        logger.info(f"Resetting thread {thread_id}")
        result = reset_thread(thread_id)
        return result
    except Exception as e:
        logger.error(f"Error resetting thread: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# WebSocket endpoint for real-time chat
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connection established for thread {thread_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            language = data.get("language", "en")
            logger.info(f"WebSocket received message for thread {thread_id}")
            
            # Process message
            response = await chat(message, thread_id, language)
            
            # Send response back to client
            await websocket.send_json(response)
            logger.info(f"WebSocket sent response for thread {thread_id}")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for thread {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error for thread {thread_id}: {str(e)}", exc_info=True)
        try:
            # Default error message
            error_message = "I apologize, but I encountered an error. Please try again."
            
            # Get language from the last request if available
            language = "en"
            if "data" in locals() and isinstance(data, dict):
                language = data.get("language", "en")
            
            # Localized error messages
            if language == "es":
                error_message = "Lo siento, encontré un error. Por favor, inténtalo de nuevo."
            elif language == "fr":
                error_message = "Je m'excuse, mais j'ai rencontré une erreur. Veuillez réessayer."
            elif language == "de":
                error_message = "Ich entschuldige mich, aber ich bin auf einen Fehler gestoßen. Bitte versuchen Sie es erneut."
            elif language == "he":
                error_message = "אני מתנצל, אבל נתקלתי בשגיאה. אנא נסה שוב."
            elif language == "ar":
                error_message = "أعتذر، لكنني واجهت خطأ. يرجى المحاولة مرة أخرى."
            
            await websocket.send_json({
                "text": error_message,
                "error": str(e),
                "language": language
            })
        except:
            pass

# Mount static files
try:
    app.mount("/", StaticFiles(directory="src/static", html=True), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.error(f"Failed to mount static files: {str(e)}")
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return """
        <html>
            <head>
                <title>Babywise Chatbot</title>
            </head>
            <body>
                <h1>Welcome to Babywise Chatbot</h1>
                <p>The static files could not be mounted. Please check the logs.</p>
            </body>
        </html>
        """

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Server starting up")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutting down")

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Babywise Chatbot Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=args.port) 