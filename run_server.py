"""
Babywise Assistant - Server Entry Point

This is the main entry point for the Babywise Assistant server.
It imports and runs the FastAPI application from the backend package.
"""

import os
import logging
from dotenv import load_dotenv
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Import the app here to ensure environment variables are loaded first
    from backend.app import app
    
    # Get configuration from environment
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    
    # Log startup configuration
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    # Run the server
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    ) 