"""
Babywise Assistant - Server

This module implements a simple server to serve the frontend and connect to the backend API.
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine the root directory
ROOT_DIR = Path(__file__).parent

# Load environment variables from .env file
# Try multiple possible locations for the .env file
possible_paths = [
    ROOT_DIR / '.env',                 # Project root
    Path.cwd() / '.env',               # Current working directory
]

for dotenv_path in possible_paths:
    if dotenv_path.exists():
        logger.info(f"Found .env file at: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
        if 'OPENAI_API_KEY' in os.environ and os.environ['OPENAI_API_KEY']:
            logger.info(f"Successfully loaded OpenAI API key from {dotenv_path}")
            break

from backend.api.main import app as backend_app

# Create FastAPI app
app = FastAPI(
    title="Babywise Assistant",
    description="A chatbot for baby care advice and routine tracking",
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

# Mount static files
frontend_dir = ROOT_DIR / "frontend"
app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

# Include backend API routes
app.mount("/api", backend_app)

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML"""
    return FileResponse(str(frontend_dir / "index.html"))

# Run the application
if __name__ == "__main__":
    # Try to find an available port starting from the default
    default_port = int(os.environ.get("PORT", 8000))
    max_port_attempts = 10
    
    for port_offset in range(max_port_attempts):
        port = default_port + port_offset
        try:
            logger.info(f"Attempting to start server on port {port}...")
            uvicorn.run(app, host="0.0.0.0", port=port)
            break  # If successful, exit the loop
        except OSError as e:
            if "address already in use" in str(e).lower():
                logger.warning(f"Port {port} is already in use, trying next port...")
                if port_offset == max_port_attempts - 1:
                    logger.error(f"Could not find an available port after {max_port_attempts} attempts")
                    raise
            else:
                # If it's a different error, re-raise it
                logger.error(f"Error starting server: {str(e)}")
                raise 