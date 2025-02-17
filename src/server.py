from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.services.agent_factory import AgentFactory
from src.services.chat_session import ChatSession
from src.database.db_manager import DatabaseManager
from src.config import Config
from src.services.llm_service import LLMService
from src.config import ResponseTypes

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist
static_dir = Path("src/static")
static_dir.mkdir(parents=True, exist_ok=True)

# Serve static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Store chat sessions and services
chat_sessions = {}
llm_service = None
agent_factory = None

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize DB
        db = DatabaseManager()
        db.create_tables()
        
        # Validate config
        Config.validate()
        
        # Initialize services
        global llm_service, agent_factory
        llm_service = LLMService(
            api_key=os.getenv('OPENAI_API_KEY'),
            model=os.getenv('MODEL_NAME', 'gpt-4')
        )
        agent_factory = AgentFactory(llm_service)
        print("Startup completed successfully")
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

@app.get("/")
async def read_root():
    try:
        index_path = static_dir / "index.html"
        if not index_path.exists():
            return PlainTextResponse("Welcome to Babywise Assistant API")
        return FileResponse(str(index_path))
    except Exception as e:
        print(f"Error serving root: {str(e)}")
        return PlainTextResponse("Error loading page")

@app.get("/favicon.ico")
async def favicon():
    try:
        favicon_path = static_dir / "favicon.ico"
        if not favicon_path.exists():
            return PlainTextResponse("")
        return FileResponse(str(favicon_path))
    except Exception as e:
        print(f"Error serving favicon: {str(e)}")
        return PlainTextResponse("")

@app.post("/chat")
async def chat(message: ChatMessage) -> Dict:
    """Process chat messages with enhanced error handling and response tracking"""
    try:
        print(f"\n=== Processing Chat Request ===")
        print(f"Message: {message.message}")
        print(f"Session ID: {message.session_id}")

        # Get or create chat session
        if message.session_id not in chat_sessions:
            print(f"Creating new chat session: {message.session_id}")
            chat_sessions[message.session_id] = ChatSession(agent_factory)
        
        session = chat_sessions[message.session_id]
        print("Chat session retrieved successfully")

        # Process the message
        try:
            print("Processing message through chat session...")
            response = await session.process_query(message.message)
            
            if not response:
                print("Warning: Empty response received")
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I apologize, but I couldn't generate a response. Could you please rephrase your question?"
                }
            
            if not isinstance(response, dict) or 'text' not in response:
                print(f"Warning: Invalid response format: {response}")
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I encountered an issue processing your request. Could you please provide more details about what you're looking for?"
                }
            
            print(f"Response generated successfully: {response.get('type', 'unknown type')}")
            return response

        except Exception as session_error:
            print(f"Error in chat session: {str(session_error)}")
            error_type = type(session_error).__name__
            
            if 'API' in error_type:
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I'm having trouble accessing external services. Please try again in a moment."
                }
            elif 'Context' in error_type:
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I need some more information to help you. Could you provide more details?"
                }
            else:
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I encountered an unexpected issue. Could you rephrase your question?"
                }

    except Exception as e:
        print(f"Critical server error: {str(e)}")
        return {
            'type': ResponseTypes.ERROR,
            'text': "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
        }

@app.get("/health")
async def health_check() -> Dict:
    return {"status": "healthy"}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str) -> Dict:
    if session_id in chat_sessions:
        chat_sessions[session_id].reset()
        return {"status": "cleared"}
    return {"status": "not_found"}

# For local development only
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8004, reload=True) 