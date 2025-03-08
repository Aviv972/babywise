import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_app")

try:
    # Add the parent directory to sys.path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Log environment variables (excluding sensitive info)
    logger.info("Python version: %s", sys.version)
    logger.info("Current directory: %s", os.getcwd())
    logger.info("Directory contents: %s", os.listdir())
    
    # Import the FastAPI app from the backend module
    from backend.app import app
    logger.info("Successfully imported app from backend.app")
    
    # This is required for Vercel serverless deployment
    app = app
    
except Exception as e:
    logger.error("Error during initialization: %s", str(e), exc_info=True)
    # Create a minimal app for error reporting
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    async def error_root():
        return {"status": "error", "message": str(e)} 