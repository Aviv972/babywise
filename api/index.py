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
    logger.info("Importing aioredis_patch module...")
    from api.aioredis_patch import patch_result as aioredis_patch_result
    logger.info(f"aioredis patch result: {aioredis_patch_result}")
    
    # Verify we can import AuthenticationError
    try:
        from aioredis.exceptions import AuthenticationError
        logger.info(f"Successfully imported AuthenticationError: {AuthenticationError}")
    except ImportError as e:
        logger.error(f"Failed to import AuthenticationError after patching: {e}")
        logger.error(traceback.format_exc())
        
        # Try to diagnose the issue
        try:
            import aioredis
            logger.info(f"aioredis module: {aioredis}")
            logger.info(f"aioredis module location: {aioredis.__file__}")
            
            import aioredis.exceptions
            logger.info(f"aioredis.exceptions module: {aioredis.exceptions}")
            logger.info(f"Available attributes in aioredis.exceptions: {dir(aioredis.exceptions)}")
        except Exception as e2:
            logger.error(f"Error diagnosing aioredis: {e2}")
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
    logger.info("Successfully imported thread_summary module")
except Exception as e:
    logger.error(f"Failed to import thread_summary module: {str(e)}")
    # Define a fallback function if import fails
    async def thread_summary_fallback(thread_id: str, request: Request, backend_available: bool = False):
        return JSONResponse({
            "error": "Thread summary module not available",
            "status": "error"
        })

# Import chat router separately to ensure it's always defined
chat_router = None
try:
    # First try to import directly from backend.api.chat
    try:
        import backend.api.chat
        logger.info(f"Successfully imported backend.api.chat module: {backend.api.chat}")
        from backend.api.chat import router as chat_router
        logger.info(f"Successfully imported chat router: {chat_router}")
    except Exception as e:
        logger.error(f"Failed to import backend.api.chat module: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Try alternative import path
        from backend.api.chat import router as chat_router
        logger.info("Successfully imported chat router via alternative path")
except Exception as e:
    logger.error(f"Failed to import chat router: {str(e)}")
    logger.error(traceback.format_exc())
    
    # Create a minimal fallback router
    from fastapi import APIRouter
    chat_router = APIRouter(prefix="/chat")
    
    @chat_router.post("")
    async def chat_fallback():
        return JSONResponse({
            "response": "Chat service is currently unavailable. Please try again later.",
            "command_processed": False,
            "command_type": None,
            "command_data": None
        })
    
    @chat_router.get("/context/{thread_id}")
    async def get_context_fallback(thread_id: str):
        return JSONResponse({
            "error": "Context service is currently unavailable",
            "status": "error"
        })
    
    @chat_router.post("/reset/{thread_id}")
    async def reset_thread_fallback(thread_id: str):
        return JSONResponse({
            "error": "Reset service is currently unavailable",
            "status": "error"
        })
    logger.info("Created fallback chat router")

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

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models directly
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    language: Optional[str] = "en"
    local_event_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    command_processed: bool = False
    command_type: Optional[str] = None
    command_data: Optional[Dict[str, Any]] = None

# Direct implementation of chat endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def direct_chat(request: ChatRequest):
    """
    Direct implementation of the chat endpoint to bypass import issues.
    """
    logger.info(f"Direct chat endpoint called with message: {request.message}")
    
    try:
        # Try to use the backend chat implementation if available
        try:
            import backend.workflow.workflow as workflow
            import backend.services.redis_service as redis_service
            from backend.models.message_types import HumanMessage, AIMessage
            
            logger.info("Successfully imported backend modules")
            
            # Get or create thread ID
            thread_id = request.thread_id or f"default_{request.language}"
            
            # Try to get thread state from Redis
            state = None
            try:
                state = await redis_service.get_thread_state(thread_id)
                logger.info(f"Retrieved thread state from Redis for {thread_id}")
            except Exception as e:
                logger.error(f"Error retrieving thread state: {str(e)}")
            
            # Create new state if not found
            if not state:
                state = workflow.get_default_state()
                state["metadata"]["language"] = request.language
                state["metadata"]["thread_id"] = thread_id
                logger.info(f"Created new thread state for {thread_id}")
            
            # Add user message to state
            user_message = HumanMessage(content=request.message)
            state["messages"].append(user_message)
            
            # Get workflow instance
            workflow_instance = await workflow.get_workflow()
            
            if workflow_instance:
                # Process the message
                result = await workflow_instance.invoke(state)
                
                # Get the last message (AI response)
                last_message = result["messages"][-1]
                if not isinstance(last_message, AIMessage):
                    last_message = AIMessage(content="I'm sorry, I couldn't process your request.")
                
                # Save thread state to Redis
                try:
                    await redis_service.save_thread_state(thread_id, result)
                    logger.info(f"Saved thread state to Redis for {thread_id}")
                except Exception as e:
                    logger.error(f"Error saving thread state: {str(e)}")
                
                # Check if command was processed
                command_processed = result.get("skip_chat", False)
                command_data = None
                command_type = None
                
                if command_processed and "command_result" in result:
                    command_result = result["command_result"]
                    command_type = command_result.get("response_type")
                    command_data = command_result.get("event_data")
                
                return ChatResponse(
                    response=last_message.content,
                    command_processed=command_processed,
                    command_type=command_type,
                    command_data=command_data
                )
            else:
                logger.error("Failed to initialize workflow")
                raise Exception("Failed to initialize workflow")
                
        except Exception as e:
            logger.error(f"Error using backend chat implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return ChatResponse(
            response=f"I apologize, but I'm having trouble processing your request. The system is experiencing technical difficulties.",
            command_processed=False,
            command_type=None,
            command_data=None
        )

@app.get("/api/chat/context/{thread_id}")
async def direct_get_context(thread_id: str):
    """
    Direct implementation of the context endpoint to bypass import issues.
    """
    logger.info(f"Direct context endpoint called for thread: {thread_id}")
    
    try:
        # Try to use the backend implementation if available
        try:
            import backend.services.redis_service as redis_service
            
            # Get thread state from Redis
            state = await redis_service.get_thread_state(thread_id)
            
            if state:
                # Extract messages
                messages = []
                for msg in state.get("messages", []):
                    msg_type = "human" if msg.get("type") == "human" else "ai"
                    messages.append({
                        "content": msg.get("content", ""),
                        "type": msg_type
                    })
                
                return JSONResponse({
                    "thread_id": thread_id,
                    "messages": messages,
                    "status": "success"
                })
            else:
                return JSONResponse({
                    "thread_id": thread_id,
                    "messages": [],
                    "status": "empty"
                })
                
        except Exception as e:
            logger.error(f"Error using backend context implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct context endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return JSONResponse({
            "thread_id": thread_id,
            "messages": [],
            "status": "error",
            "error": str(e)
        })

@app.post("/api/chat/reset/{thread_id}")
async def direct_reset_thread(thread_id: str):
    """
    Direct implementation of the reset endpoint to bypass import issues.
    """
    logger.info(f"Direct reset endpoint called for thread: {thread_id}")
    
    try:
        # Try to use the backend implementation if available
        try:
            import backend.services.redis_service as redis_service
            
            # Delete thread state from Redis
            success = await redis_service.delete_thread_state(thread_id)
            
            if success:
                return JSONResponse({
                    "thread_id": thread_id,
                    "status": "success",
                    "message": "Thread reset successfully"
                })
            else:
                return JSONResponse({
                    "thread_id": thread_id,
                    "status": "error",
                    "message": "Failed to reset thread"
                })
                
        except Exception as e:
            logger.error(f"Error using backend reset implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct reset endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return JSONResponse({
            "thread_id": thread_id,
            "status": "error",
            "error": str(e)
        })

# Mount routers
try:
    app.include_router(chat_router, prefix="/api")
    logger.info("Mounted chat router")
except Exception as e:
    logger.error(f"Failed to mount chat router: {str(e)}")
    logger.error(traceback.format_exc())

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

# Direct implementation of routine endpoints
@app.get("/api/routines/events")
async def direct_get_events(thread_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Direct implementation of the get events endpoint to bypass import issues.
    """
    logger.info(f"Direct get events endpoint called for thread: {thread_id}")
    
    try:
        # Try to use the backend implementation if available
        try:
            import backend.db.routine_db as routine_db
            
            events = await routine_db.get_events(thread_id, start_date, end_date)
            
            return JSONResponse({
                "events": events,
                "status": "success"
            })
                
        except Exception as e:
            logger.error(f"Error using backend get events implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct get events endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return JSONResponse({
            "events": [],
            "status": "error",
            "error": str(e)
        })

@app.post("/api/routines/events")
async def direct_add_event(request: Request):
    """
    Direct implementation of the add event endpoint to bypass import issues.
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Direct add event endpoint called with body: {body}")
        
        # Try to use the backend implementation if available
        try:
            import backend.db.routine_db as routine_db
            
            event = await routine_db.add_event(
                thread_id=body.get("thread_id"),
                event_type=body.get("event_type"),
                event_time=body.get("event_time"),
                event_data=body.get("event_data"),
                local_id=body.get("local_id")
            )
            
            return JSONResponse({
                "event": event,
                "status": "success"
            })
                
        except Exception as e:
            logger.error(f"Error using backend add event implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct add event endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return JSONResponse({
            "status": "error",
            "error": str(e)
        })

@app.get("/api/routines/events/latest/{thread_id}/{event_type}")
async def direct_get_latest_event(thread_id: str, event_type: str):
    """
    Direct implementation of the get latest event endpoint to bypass import issues.
    """
    logger.info(f"Direct get latest event endpoint called for thread: {thread_id}, event type: {event_type}")
    
    try:
        # Try to use the backend implementation if available
        try:
            import backend.db.routine_db as routine_db
            
            event = await routine_db.get_latest_event(thread_id, event_type)
            
            return JSONResponse({
                "event": event,
                "status": "success"
            })
                
        except Exception as e:
            logger.error(f"Error using backend get latest event implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct get latest event endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return JSONResponse({
            "event": None,
            "status": "error",
            "error": str(e)
        })

@app.get("/api/routines/summary/{thread_id}")
async def direct_get_summary(thread_id: str, period: str = "day"):
    """
    Direct implementation of the get summary endpoint to bypass import issues.
    """
    logger.info(f"Direct get summary endpoint called for thread: {thread_id}, period: {period}")
    
    try:
        # Try to use the backend implementation if available
        try:
            import backend.db.routine_db as routine_db
            
            summary = await routine_db.get_summary(thread_id, period)
            
            return JSONResponse({
                "summary": summary,
                "status": "success"
            })
                
        except Exception as e:
            logger.error(f"Error using backend get summary implementation: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    except Exception as e:
        logger.error(f"Error in direct get summary endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return JSONResponse({
            "summary": {
                "sleep": {"total_duration": 0, "events": []},
                "feed": {"total_count": 0, "events": []}
            },
            "status": "error",
            "error": str(e)
        })

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    logger.info("Health check endpoint called")
    
    # Check if backend modules are available
    backend_available = False
    try:
        import backend.workflow.workflow
        import backend.services.redis_service
        backend_available = True
    except Exception as e:
        logger.error(f"Backend modules not available: {str(e)}")
    
    return JSONResponse({
        "status": "ok",
        "backend_available": backend_available,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
