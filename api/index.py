#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import traceback
import logging
import json
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Import aioredis patch before any other imports
try:
    from api.aioredis_patch import patch_result as aioredis_patch_result
    logger.info(f"aioredis patch result: {aioredis_patch_result}")
except Exception as e:
    logger.error(f"Failed to import aioredis patch: {str(e)}")
    logger.error(traceback.format_exc())

# Now import the rest of the modules
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union

# Import compatibility patches
from api.compatibility import apply_all_patches

# Apply all compatibility patches
patch_results = apply_all_patches()
logger.info(f"Compatibility patch results: {patch_results}")

# Add the project root to the Python path first
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
logger.info(f"Added {root_dir} to Python path")

# Ensure environment variables are set
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
os.environ.setdefault("STORAGE_URL", os.environ.get("STORAGE_URL", ""))

# The compatibility module will handle environment setup for read-only filesystems

# Import compatibility module to apply patches before any other imports
try:
    logger.info("Importing compatibility module")
    from api.compatibility import patch_results
    logger.info(f"Compatibility patches applied: {patch_results}")
except Exception as e:
    logger.error(f"Failed to import compatibility module: {str(e)}")
    logger.error(traceback.format_exc())

# Now import other modules
from typing import Dict, Any, Optional, List, ForwardRef, cast

# Now import FastAPI and related modules
try:
    import fastapi
    import pydantic
    import starlette
    from fastapi import FastAPI, Request, Response, HTTPException, Depends
    from fastapi.responses import JSONResponse, HTMLResponse, Response
    from fastapi.middleware.cors import CORSMiddleware
    
    logger.info(f"Successfully imported FastAPI modules: {fastapi.__version__}")
except Exception as e:
    logger.error(f"Failed to import FastAPI modules: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Import custom modules
try:
    from api.thread_summary import thread_summary_fallback
    from backend.api.chat import router as chat_router
    logger.info("Successfully imported thread_summary and chat modules")
except Exception as e:
    logger.error(f"Failed to import modules: {str(e)}")
    # Define a fallback function if import fails
    async def thread_summary_fallback(thread_id: str, request: Request, backend_available: bool = False):
        return JSONResponse({
            "error": "Thread summary module not available",
            "status": "error"
        })

# Import debug modules
try:
    from api.debug_openai import router as debug_openai_router
    logger.info("Successfully imported debug_openai module")
except Exception as e:
    logger.error(f"Failed to import debug_openai module: {str(e)}")

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

# Mount routers
app.include_router(chat_router, prefix="/api")

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
