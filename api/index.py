import sys
import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_app")

# Create a simple FastAPI app for diagnostics
app = FastAPI()

@app.get("/")
async def root():
    """Root endpoint for diagnostics"""
    # Log environment info
    python_version = sys.version
    current_dir = os.getcwd()
    dir_contents = os.listdir()
    
    # Log the information
    logger.info(f"Python version: {python_version}")
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Directory contents: {dir_contents}")
    
    return {
        "status": "ok",
        "message": "Babywise API is running in diagnostic mode",
        "environment": {
            "python_version": python_version,
            "current_directory": current_dir,
            "directory_contents": dir_contents,
            "env_vars": {k: "***" for k in os.environ.keys()}
        }
    }

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "mode": "diagnostic"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)}
    )

# This is required for Vercel serverless deployment
app = app 