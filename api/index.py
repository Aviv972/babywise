"""
Babywise Assistant - Vercel Serverless Function Entry Point

This module serves as the entry point for Vercel serverless functions.
It provides a simplified version of the backend for Vercel deployment.
"""

import os
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import FastAPI and related modules
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Create a FastAPI app
app = FastAPI(title="Babywise Assistant API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add the project root to the Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))
logger.info(f"Added {root_dir} to Python path")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Try to import some core modules
        import fastapi
        import pydantic
        
        # Environment variables check
        env_vars = {
            "PYTHONPATH": os.environ.get("PYTHONPATH", "Not set"),
            "STORAGE_URL": "Available" if os.environ.get("STORAGE_URL") else "Not set",
            "OPENAI_API_KEY": "Available" if os.environ.get("OPENAI_API_KEY") else "Not set"
        }
        
        # Report status
        return {
            "status": "ok",
            "service": "Babywise API",
            "environment": env_vars,
            "timestamp": datetime.now().isoformat(),
            "versions": {
                "fastapi": fastapi.__version__,
                "pydantic": pydantic.__version__
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

# Root path handler
@app.get("/")
async def root():
    """Serve a simple HTML page at the root path."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Babywise Assistant API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .message {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 15px;
                border-left: 4px solid #28a745;
            }
        </style>
    </head>
    <body>
        <h1>Babywise Assistant API</h1>
        <div class="message">
            <p>The API is running successfully! 🎉</p>
            <p>This is the API server for the Babywise Assistant application.</p>
            <p>For more information, check the <a href="/api/health">health endpoint</a>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Debug endpoint
@app.get("/debug")
async def debug():
    """Debug endpoint to check environment variables and imports."""
    try:
        # Get environment variables
        env_vars = {k: "Available" if v else "Not set" for k, v in os.environ.items() 
                   if k in ["PYTHONPATH", "STORAGE_URL", "OPENAI_API_KEY"]}
        
        # Try to import some modules
        import_status = {}
        for module_name in ["fastapi", "pydantic", "sqlalchemy", "langchain", "openai"]:
            try:
                module = __import__(module_name)
                version = getattr(module, "__version__", "unknown")
                import_status[module_name] = {"status": "success", "version": version}
            except ImportError as e:
                import_status[module_name] = {"status": "error", "message": str(e)}
        
        return {
            "status": "ok",
            "python_version": sys.version,
            "environment": env_vars,
            "imports": import_status,
            "sys_path": sys.path
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

# Chat endpoint (simplified version for testing Vercel deployment)
@app.post("/api/chat")
async def chat(request: Request):
    """
    Simplified chat endpoint for testing Vercel deployment.
    """
    try:
        # Parse the request body
        body = await request.json()
        message = body.get("message", "")
        thread_id = body.get("thread_id", "default")
        
        logger.info(f"Received message: {message} (Thread: {thread_id})")
        
        # Return a simple response for now
        response = {
            "response": f"Echo: {message}\n\nThis is a placeholder response while we're fixing deployment issues. Your message was received and the API is working.",
            "command_processed": False,
            "command_type": None,
            "command_data": None
        }
        
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return JSONResponse({
            "response": "Sorry, an error occurred while processing your message. We're working on fixing it!",
            "command_processed": False,
            "command_type": None,
            "command_data": None
        }, status_code=200)  # Return 200 even for errors to avoid frontend errors

# Context endpoint
@app.get("/api/chat/context/{thread_id}")
async def get_context(thread_id: str):
    """
    Simplified context endpoint for testing Vercel deployment.
    """
    try:
        logger.info(f"Getting context for thread {thread_id}")
        
        # Return placeholder context
        return {
            "context": {
                "domain": "general",
                "metadata": {
                    "language": "en"
                },
                "language": "en"
            }
        }
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return {
            "context": None,
            "error": str(e)
        }

# Add more simplified endpoints as needed
