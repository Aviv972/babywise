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
import logging

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
        
        # Get environment variables with defaults
        api_key = os.getenv('OPENAI_API_KEY')
        model_name = os.getenv('MODEL_NAME', 'gpt-4')  # Default to gpt-4 if not set
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
            
        logger.info(f"Using model: {model_name}")
        
        # Initialize services
        global llm_service, agent_factory
        llm_service = LLMService(
            api_key=api_key,
            model=model_name
        )
        agent_factory = AgentFactory(llm_service)
        logger.info("Startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
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
    logger = logging.getLogger(__name__)
    logger.info("\n=== Starting Chat Request Processing ===")
    
    try:
        # Log the incoming message
        logger.info(f"Received message: {message.message}")
        logger.info(f"Session ID: {message.session_id}")

        # Log service status
        logger.info("=== Service Status Check ===")
        logger.info(f"LLM Service initialized: {bool(llm_service)}")
        logger.info(f"Agent Factory initialized: {bool(agent_factory)}")
        logger.info(f"Active chat sessions: {len(chat_sessions)}")

        # Log environment variables
        logger.info("=== Environment Variables ===")
        env_vars = {
            'OPENAI_API_KEY': bool(os.getenv('OPENAI_API_KEY')),
            'PERPLEXITY_API_KEY': bool(os.getenv('PERPLEXITY_API_KEY')),
            'MODEL_NAME': os.getenv('MODEL_NAME', 'gpt-4'),
            'PYTHONPATH': os.getenv('PYTHONPATH')
        }
        for var, value in env_vars.items():
            logger.info(f"{var}: {value}")

        # Get or create chat session
        if message.session_id not in chat_sessions:
            logger.info(f"Creating new chat session: {message.session_id}")
            if not agent_factory:
                logger.error("Agent factory not initialized!")
                raise RuntimeError("Chat service not properly initialized")
            chat_sessions[message.session_id] = ChatSession(agent_factory)
            logger.info("New chat session created successfully")
        else:
            logger.info("Using existing chat session")
        
        session = chat_sessions[message.session_id]

        # Process the message
        try:
            logger.info("=== Processing Message ===")
            logger.info("Sending message to chat session for processing...")
            response = await session.process_query(message.message)
            
            if not response:
                logger.warning("Empty response received from chat session")
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I apologize, but I couldn't generate a response. Could you please rephrase your question?"
                }
            
            if not isinstance(response, dict) or 'text' not in response:
                logger.warning(f"Invalid response format received: {response}")
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I encountered an issue processing your request. Could you please provide more details about what you're looking for?"
                }
            
            logger.info(f"Response generated successfully - Type: {response.get('type', 'unknown')}")
            logger.info(f"Response text length: {len(response.get('text', ''))}")
            return response

        except Exception as session_error:
            logger.error("=== Session Processing Error ===")
            logger.error(f"Error type: {type(session_error).__name__}")
            logger.error(f"Error message: {str(session_error)}")
            logger.error("Full traceback:", exc_info=True)
            
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
        logger.error("=== Critical Server Error ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full traceback:", exc_info=True)
        return {
            'type': ResponseTypes.ERROR,
            'text': "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
        }
    finally:
        logger.info("=== Chat Request Processing Complete ===\n")

@app.get("/health")
async def health_check() -> Dict:
    return {"status": "healthy"}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str) -> Dict:
    if session_id in chat_sessions:
        chat_sessions[session_id].reset()
        return {"status": "cleared"}
    return {"status": "not_found"} 