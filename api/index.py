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
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import FastAPI and related modules with explicit version checking
import fastapi
import pydantic
import starlette
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log dependency versions
logger.info(f"FastAPI version: {fastapi.__version__}")
logger.info(f"Pydantic version: {pydantic.__version__}")
logger.info(f"Starlette version: {starlette.__version__}")

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

# Debug endpoint to check versions
@app.get("/debug")
async def debug_versions():
    """Debug endpoint to check runtime versions."""
    try:
        # Try to import additional modules
        modules = {
            "fastapi": fastapi.__version__,
            "pydantic": pydantic.__version__,
            "starlette": starlette.__version__
        }
        
        # Try to import langchain and langgraph
        try:
            import langchain
            modules["langchain"] = langchain.__version__
        except (ImportError, AttributeError):
            modules["langchain"] = "not available"
            
        try:
            import langgraph
            modules["langgraph"] = langgraph.__version__
        except (ImportError, AttributeError):
            modules["langgraph"] = "not available"
        
        # Get Python version
        import platform
        python_version = platform.python_version()
        
        return {
            "status": "ok",
            "python_version": python_version,
            "modules": modules,
            "sys_path": sys.path
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Babywise API",
        "versions": {
            "fastapi": fastapi.__version__,
            "pydantic": pydantic.__version__
        }
    }

# Try to import the backend app
BACKEND_AVAILABLE = False
try:
    # Import backend modules
    logger.info("Attempting to import backend modules")
    
    # First, try to update forward refs in pydantic models
    # This is a workaround for the ForwardRef._evaluate issue
    try:
        from pydantic import BaseModel
        from typing import ForwardRef
        
        # Monkey patch ForwardRef._evaluate if needed
        original_evaluate = getattr(ForwardRef, "_evaluate", None)
        if original_evaluate and "recursive_guard" not in original_evaluate.__code__.co_varnames:
            logger.info("Applying ForwardRef._evaluate patch")
            
            def patched_evaluate(self, globalns, localns, recursive_guard=None):
                if recursive_guard is None:
                    recursive_guard = set()
                return original_evaluate(self, globalns, localns)
            
            ForwardRef._evaluate = patched_evaluate
            logger.info("ForwardRef._evaluate patched successfully")
    except Exception as e:
        logger.error(f"Failed to patch ForwardRef._evaluate: {str(e)}")
    
    # Now try to import the backend
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