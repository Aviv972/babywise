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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import compatibility module to apply patches before any other imports
try:
    logger.info("Importing compatibility module")
    from api.compatibility import patch_results
    logger.info(f"Compatibility patches applied: {patch_results}")
except Exception as e:
    logger.error(f"Failed to import compatibility module: {str(e)}")

# Now import other modules
from typing import Dict, Any, Optional, List, ForwardRef, cast

# Now import FastAPI and related modules
import fastapi
import pydantic
import starlette
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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

# Root path handler to serve a simple HTML page
@app.get("/", response_class=HTMLResponse)
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
            .endpoint {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 15px;
            }
            .endpoint h3 {
                margin-top: 0;
            }
            code {
                background-color: #eee;
                padding: 2px 5px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1>Babywise Assistant API</h1>
        <p>Welcome to the Babywise Assistant API. This is the API server for the Babywise Assistant application.</p>
        
        <h2>Available Endpoints:</h2>
        
        <div class="endpoint">
            <h3>Health Check</h3>
            <p><code>GET /api/health</code> - Check if the API is running</p>
        </div>
        
        <div class="endpoint">
            <h3>Debug Information</h3>
            <p><code>GET /debug</code> - Get debug information about the server environment</p>
        </div>
        
        <div class="endpoint">
            <h3>Chat API</h3>
            <p><code>POST /api/chat</code> - Send a message to the assistant</p>
        </div>
        
        <p>For more information, please refer to the API documentation.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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