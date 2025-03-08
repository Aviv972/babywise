from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.middleware.debug import DebugMiddleware
from src.config import Config
from src.routes import chat
from src.services.service_container import container

# Initialize the FastAPI app
app = FastAPI(
    title="Babywise API",
    description="API for the Babywise parenting assistant chatbot",
    version="1.0.0"
)

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

# Include routers with dependencies
app.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("Starting Babywise API...")
    print(f"Using model: {Config.MODEL_NAME}")
    print("Services initialized successfully")

@app.get("/")
async def root():
    """Root endpoint for API health check"""
    return {
        "status": "healthy",
        "service": "Babywise API",
        "version": "1.0.0"
    }