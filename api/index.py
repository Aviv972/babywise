"""
Babywise Assistant - Vercel Serverless Function Entry Point

This module serves as the entry point for Vercel serverless functions.
It imports the FastAPI app from the backend and exposes it for Vercel deployment.

The module follows the project's asynchronous programming guidelines and
provides proper error handling for the serverless environment.
"""

import sys
import os
import logging
import platform
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log Python version and environment information
logger.info(f"Python Version: {platform.python_version()}")
logger.info(f"Python Implementation: {platform.python_implementation()}")
logger.info(f"System: {platform.system()} {platform.release()}")

try:
    # Add the project root to the Python path
    root_dir = Path(__file__).parent.parent
    sys.path.append(str(root_dir))
    logger.info(f"Added {root_dir} to Python path")
    
    # Import the FastAPI app from the backend
    logger.info("Attempting to import FastAPI app from backend")
    from backend.api.main import app
    logger.info("Successfully imported FastAPI app from backend")
    
except ImportError as e:
    logger.error(f"Failed to import FastAPI app: {str(e)}")
    logger.error(f"Python path: {sys.path}")
    
    # Provide a fallback app for error reporting
    from fastapi import FastAPI, HTTPException
    
    app = FastAPI()
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint that will work even if main app fails to load."""
        return {
            "status": "error", 
            "message": "Application failed to initialize properly",
            "python_version": platform.python_version(),
            "system": f"{platform.system()} {platform.release()}"
        }
    
    @app.get("/api/{path:path}")
    async def error_response(path: str):
        """Catch-all route that returns an error for all API requests."""
        raise HTTPException(
            status_code=500, 
            detail="Application failed to initialize. Check server logs for details."
        )

# Export the app for Vercel
app = app 