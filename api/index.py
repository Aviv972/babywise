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
import base64
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
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# Import custom modules
try:
    from api.thread_summary import thread_summary_fallback
    logger.info("Successfully imported thread_summary module")
except Exception as e:
    logger.error(f"Failed to import thread_summary module: {str(e)}")
    # Define a fallback function if import fails
    async def thread_summary_fallback(thread_id: str, request: Request, backend_available: bool = False):
        return JSONResponse({
            "error": "Thread summary module not available",
            "status": "error"
        })

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
        <link rel="icon" href="/favicon.ico" type="image/x-icon">
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

# Favicon handler to prevent 404 errors
@app.get("/favicon.ico")
async def favicon():
    """Serve a simple favicon to prevent 404 errors."""
    # This is a minimal 16x16 favicon (base64 encoded)
    favicon_base64 = "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAABILAAASCwAAAAAAAAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAA=="
    
    # Decode the base64 string to bytes
    favicon_bytes = base64.b64decode(favicon_base64)
    
    # Return the favicon with the appropriate content type
    return Response(content=favicon_bytes, media_type="image/x-icon")

# Also handle favicon.png for browsers that prefer PNG
@app.get("/favicon.png")
async def favicon_png():
    """Redirect to favicon.ico for simplicity."""
    return Response(status_code=307, headers={"Location": "/favicon.ico"})

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
    
    # Set up environment variables that might be needed by the backend
    os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    os.environ.setdefault("STORAGE_URL", os.environ.get("STORAGE_URL", ""))
    
    # Create a mock .env file if it doesn't exist
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        logger.info(f"Creating mock .env file at {env_path}")
        with open(env_path, 'w') as f:
            f.write(f"OPENAI_API_KEY={os.environ.get('OPENAI_API_KEY', '')}\n")
            f.write(f"STORAGE_URL={os.environ.get('STORAGE_URL', '')}\n")
    
    # Now try to import the backend
    try:
        from backend.api.main import app as backend_app
        
        # Use the backend app's routes
        app.routes.extend(backend_app.routes)
        logger.info("Successfully imported backend routes")
        
        # Import successful, use the backend app
        BACKEND_AVAILABLE = True
    except ImportError as e:
        logger.error(f"ImportError when importing backend app: {str(e)}")
        # Try to import specific modules to diagnose the issue
        try:
            import backend
            logger.info("Successfully imported backend package")
            
            import backend.api
            logger.info("Successfully imported backend.api package")
            
            # If we got here, the issue is with backend.api.main specifically
            logger.error("Issue is with backend.api.main module")
        except ImportError as e2:
            logger.error(f"Failed to import backend packages: {str(e2)}")
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

# Add a specific endpoint for thread-based summary requests
@app.get("/api/routines/summary/{thread_id}")
async def thread_summary_route(thread_id: str, request: Request):
    """Route for thread-specific summary requests."""
    try:
        # Get query parameters
        period = request.query_params.get("period", "day")
        
        # Log the request
        logger.info(f"Received thread summary request: thread_id={thread_id}, period={period}")
        
        # Return an empty response with thread_id
        return JSONResponse({
            "thread_id": thread_id,
            "period": period,
            "summary": {
                "sleep_events": [],
                "feed_events": [],
                "total_sleep_duration": 0,
                "total_feeds": 0
            },
            "status": "limited",
            "message": "Summary functionality is currently unavailable."
        })
    except Exception as e:
        logger.error(f"Error in thread_summary_route: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

# Debug endpoint for backend import status
@app.get("/debug/backend")
async def debug_backend():
    """Debug endpoint to check backend import status."""
    try:
        # Check if backend directory exists
        backend_dir = Path(__file__).parent.parent / "backend"
        backend_exists = backend_dir.exists()
        
        # Check if backend/__init__.py exists
        backend_init = backend_dir / "__init__.py"
        backend_init_exists = backend_init.exists()
        
        # Check if backend/api directory exists
        backend_api_dir = backend_dir / "api"
        backend_api_exists = backend_api_dir.exists()
        
        # Check if backend/api/__init__.py exists
        backend_api_init = backend_api_dir / "__init__.py"
        backend_api_init_exists = backend_api_init.exists()
        
        # Check if backend/api/main.py exists
        backend_api_main = backend_api_dir / "main.py"
        backend_api_main_exists = backend_api_main.exists()
        
        # Try to import backend modules
        backend_import_error = None
        try:
            import backend
            backend_imported = True
        except ImportError as e:
            backend_imported = False
            backend_import_error = str(e)
        
        # Try to import backend.api
        backend_api_import_error = None
        try:
            import backend.api
            backend_api_imported = True
        except ImportError as e:
            backend_api_imported = False
            backend_api_import_error = str(e)
        
        # Try to import backend.api.main
        backend_api_main_import_error = None
        try:
            import backend.api.main
            backend_api_main_imported = True
        except ImportError as e:
            backend_api_main_imported = False
            backend_api_main_import_error = str(e)
        except Exception as e:
            backend_api_main_imported = False
            backend_api_main_import_error = f"Error: {str(e)}"
        
        return {
            "backend_available": BACKEND_AVAILABLE,
            "diagnostics": {
                "backend_dir_exists": backend_exists,
                "backend_init_exists": backend_init_exists,
                "backend_api_dir_exists": backend_api_exists,
                "backend_api_init_exists": backend_api_init_exists,
                "backend_api_main_exists": backend_api_main_exists,
                "backend_imported": backend_imported,
                "backend_import_error": backend_import_error,
                "backend_api_imported": backend_api_imported,
                "backend_api_import_error": backend_api_import_error,
                "backend_api_main_imported": backend_api_main_imported,
                "backend_api_main_import_error": backend_api_main_import_error,
                "python_path": sys.path
            }
        }
    except Exception as e:
        logger.error(f"Error in debug_backend: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
