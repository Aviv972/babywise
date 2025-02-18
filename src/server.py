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
from src.services.service_container import container

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

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize DB
        db = DatabaseManager()
        db.create_tables()
        
        # Log environment variables
        logger = logging.getLogger(__name__)
        logger.info("=== Environment Variables ===")
        env_vars = {
            'OPENAI_API_KEY': bool(os.getenv('OPENAI_API_KEY')),
            'PERPLEXITY_API_KEY': bool(os.getenv('PERPLEXITY_API_KEY')),
            'MODEL_NAME': os.getenv('MODEL_NAME', 'gpt-4'),
            'PYTHONPATH': os.getenv('PYTHONPATH')
        }
        for var, value in env_vars.items():
            logger.info(f"{var}: {value}")
            
        # Services are initialized through the container
        logger.info("Services initialized through container")
        logger.info(f"Using model: {container.llm_service.model}")
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

@app.get("/health")
async def health_check() -> Dict:
    return {"status": "healthy"}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str) -> Dict:
    if session_id in chat_sessions:
        chat_sessions[session_id].reset()
        return {"status": "cleared"}
    return {"status": "not_found"} 