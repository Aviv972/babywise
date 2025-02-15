from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from typing import List, Dict
import uvicorn
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.agent_manager import AgentManager
from src.agents.pregnancy_agent import PregnancyAgent
from src.agents.baby_gear_agent import BabyGearAgent
from src.agents.sleep_routine_agent import SleepRoutineAgent
from src.agents.feeding_agent import FeedingAgent
from src.agents.hygiene_agent import HygieneAgent
from src.agents.parenting_challenges_agent import ParentingChallengesAgent
from src.agents.budget_agent import BudgetAgent
from src.agents.safety_agent import SafetyAgent
from src.agents.community_support_agent import CommunityAgent
from src.services.llm_service import LLMService
from src.config import Config
from src.agents.medical_health_agent import MedicalHealthAgent
from src.agents.travel_agent import TravelAgent
from src.agents.emergency_agent import EmergencyAgent
from src.agents.education_agent import EducationAgent
from src.agents.development_agent import DevelopmentAgent
from src.services.agent_factory import AgentFactory
from src.services.chat_session import ChatSession
from src.database.db_manager import DatabaseManager

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Store chat sessions
chat_sessions = {}

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

@app.on_event("startup")
async def startup_event():
    # Initialize DB
    db = DatabaseManager()
    db.create_tables()
    # Validate config
    Config.validate()

@app.get("/")
async def read_root():
    return FileResponse("src/static/index.html")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("src/static/favicon.ico")

@app.post("/chat")
async def chat(message: ChatMessage) -> Dict:
    try:
        if message.session_id not in chat_sessions:
            chat_sessions[message.session_id] = ChatSession(AgentFactory())

        response = await chat_sessions[message.session_id].process_query(message.message)
        return response

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e)
            }
        )

@app.get("/health")
async def health_check() -> Dict:
    return {"status": "healthy"}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str) -> Dict:
    if session_id in chat_sessions:
        chat_sessions[session_id].reset()
        return {"status": "cleared"}
    return {"status": "not_found"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8004, reload=True) 