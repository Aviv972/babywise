import asyncio
from agent_manager import AgentManager
from agents.pregnancy_agent import PregnancyAgent
from services.llm_service import OpenAIService
from config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.middleware.debug import DebugMiddleware

app = FastAPI()

# Add debug middleware first
app.add_middleware(DebugMiddleware)

# Then add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from src.routes import chat
app.include_router(chat.router)

async def main():
    # Load and validate configuration
    Config.validate()
    
    # Initialize LLM service securely
    llm_service = OpenAIService(
        api_key=Config.get_api_key(),
        model=Config.OPENAI_MODEL
    )
    
    # Initialize the agent manager
    manager = AgentManager()
    
    # Register agents
    pregnancy_agent = PregnancyAgent(llm_service=llm_service)
    manager.register_agent(pregnancy_agent)
    
    # Start a conversation
    pregnancy_agent.start_conversation(user_id="test_user")
    
    # Example usage
    queries = [
        "What helps with morning sickness?",
        "When should I get my first ultrasound?",
        "How do I prepare for labor?"
    ]
    
    for query in queries:
        response = await manager.process_query(query)
        print(f"Q: {query}")
        print(f"A: {response}\n")
    
    # Show conversation history
    print("Recent conversation history:")
    history = pregnancy_agent.get_recent_context()
    for msg in history:
        print(f"Time: {msg['timestamp']}")
        print(f"Q: {msg['query']}")
        print(f"A: {msg['response']}\n")

if __name__ == "__main__":
    asyncio.run(main()) 