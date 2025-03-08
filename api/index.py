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
import json
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

# Try to import the backend app
try:
    # Import the backend app
    logger.info("Attempting to import backend modules")
    from backend.api.main import app as backend_app
    
    # Use the backend app's routes
    app.routes.extend(backend_app.routes)
    logger.info("Successfully imported backend routes")
    
    # Import successful, use the backend app
    BACKEND_AVAILABLE = True
except Exception as e:
    # Log the error
    logger.error(f"Failed to import backend app: {str(e)}")
    logger.error(f"Python path: {sys.path}")
    
    # Backend import failed, provide fallback functionality
    BACKEND_AVAILABLE = False

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    if BACKEND_AVAILABLE:
        return {"status": "ok", "backend": "available"}
    else:
        return {
            "status": "limited", 
            "backend": "unavailable", 
            "message": "Backend services are currently unavailable. Basic functionality only."
        }

# Fallback chat endpoint if backend is not available
@app.post("/api/chat")
async def chat_fallback(request: Request):
    """Fallback chat endpoint when backend is unavailable."""
    if BACKEND_AVAILABLE:
        # This should not be called if backend is available
        # as the backend routes should handle this endpoint
        raise HTTPException(
            status_code=500,
            detail="Internal routing error. Please try again."
        )
    
    try:
        # Parse the request body
        body = await request.json()
        message = body.get("message", "")
        thread_id = body.get("thread_id", "")
        language = body.get("language", "en")
        
        # Log the request
        logger.info(f"Received chat request: thread_id={thread_id}, language={language}")
        
        # Provide a fallback response
        if language == "he":
            response_text = "מצטערים, השירות אינו זמין כרגע. אנא נסה שוב מאוחר יותר."
        else:
            response_text = "Sorry, the service is currently unavailable. Please try again later."
        
        # Return a fallback response
        return JSONResponse({
            "response": response_text,
            "thread_id": thread_id,
            "language": language,
            "status": "error",
            "error": "Backend services unavailable"
        })
    except Exception as e:
        logger.error(f"Error in chat_fallback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

# Fallback context endpoint if backend is not available
@app.get("/api/chat/context/{thread_id}")
async def context_fallback(thread_id: str):
    """Fallback context endpoint when backend is unavailable."""
    if BACKEND_AVAILABLE:
        # This should not be called if backend is available
        # as the backend routes should handle this endpoint
        raise HTTPException(
            status_code=500,
            detail="Internal routing error. Please try again."
        )
    
    try:
        # Log the request
        logger.info(f"Received context request: thread_id={thread_id}")
        
        # Return an empty context
        return JSONResponse({
            "thread_id": thread_id,
            "context": {},
            "status": "limited"
        })
    except Exception as e:
        logger.error(f"Error in context_fallback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

# Fallback routines endpoint if backend is not available
@app.get("/api/routines/events")
@app.post("/api/routines/events")
async def routines_fallback(request: Request):
    """Fallback routines endpoint when backend is unavailable."""
    if BACKEND_AVAILABLE:
        # This should not be called if backend is available
        # as the backend routes should handle this endpoint
        raise HTTPException(
            status_code=500,
            detail="Internal routing error. Please try again."
        )
    
    try:
        # Log the request
        logger.info(f"Received routines request: method={request.method}")
        
        # Return an empty response
        return JSONResponse({
            "events": [],
            "status": "limited",
            "message": "Routine tracking is currently unavailable."
        })
    except Exception as e:
        logger.error(f"Error in routines_fallback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

# Fallback summary endpoint if backend is not available
@app.get("/api/routines/summary")
async def summary_fallback(request: Request):
    """Fallback summary endpoint when backend is unavailable."""
    if BACKEND_AVAILABLE:
        # This should not be called if backend is available
        # as the backend routes should handle this endpoint
        raise HTTPException(
            status_code=500,
            detail="Internal routing error. Please try again."
        )
    
    try:
        # Log the request
        logger.info(f"Received summary request: method={request.method}")
        
        # Return an empty response
        return JSONResponse({
            "summary": {},
            "status": "limited",
            "message": "Summary functionality is currently unavailable."
        })
    except Exception as e:
        logger.error(f"Error in summary_fallback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

# Export the app for Vercel
app = app 