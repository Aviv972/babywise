#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import traceback
import logging
import json
import asyncio
import contextlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, AsyncGenerator


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("=== API STARTUP ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"File location: {__file__}")
# Don't access event loop during module initialization
# logger.info(f"Event loop: {asyncio.get_running_loop()}")

# Import Redis modules
import redis

# Remove old aioredis patch import
logger.info("Using redis.asyncio for Redis operations")

# Now import the rest of the modules
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid

# Import compatibility patches
from backend.api.compatibility import apply_all_patches

# Apply all compatibility patches
patch_results = apply_all_patches()
logger.info(f"Compatibility patch results: {patch_results}")

# Add the project root to the Python path first
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
logger.info(f"Added {root_dir} to Python path")

# Ensure environment variables are set
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
os.environ.setdefault("STORAGE_URL", os.environ.get("STORAGE_URL", ""))

# The compatibility module will handle environment setup for read-only filesystems

# Import compatibility module to apply patches before any other imports
try:
    logger.info("Importing compatibility module")
    from backend.api.compatibility import patch_results
    logger.info(f"Compatibility patches applied: {patch_results}")
except Exception as e:
    logger.error(f"Failed to import compatibility module: {str(e)}")
    logger.error(traceback.format_exc())

# Now import other modules
from typing import Dict, Any, Optional, List, ForwardRef, cast

# Import message type classes that are used in the chat endpoint
from langchain_core.messages import HumanMessage, AIMessage

# Now import FastAPI and related modules
try:
    import fastapi
    import pydantic
    import starlette
    from fastapi import FastAPI, Request, Response, HTTPException, Depends
    from fastapi.responses import JSONResponse, HTMLResponse, Response
    logger.info(f"FastAPI version: {fastapi.__version__}")
    logger.info(f"Pydantic version: {pydantic.__version__}")
    logger.info(f"Starlette version: {starlette.__version__}")
except Exception as e:
    logger.error(f"Failed to import web framework modules: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Redis connection configuration
REDIS_URL = os.environ.get("STORAGE_URL", "redis://localhost:6379/0")

# In-memory fallback cache when Redis is unavailable
_memory_cache = {}

@contextlib.asynccontextmanager
async def redis_connection() -> AsyncGenerator[Optional[redis.asyncio.Redis], None]:
    """
    Context manager for Redis connections to ensure proper cleanup.
    
    This creates a completely isolated connection for a single operation
    and guarantees it will be properly closed regardless of success or failure.
    
    Usage:
        async with redis_connection() as redis:
            if redis:
                # Use redis connection here
                await redis.get("my_key")
    """
    client = None
    try:
        # Ensure we have an event loop - in serverless environments, this might
        # not be available during module initialization, but should be during request handling
        try:
            # Get the current event loop or create a new one if none exists
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running event loop, create a new one if none exists
                # This should only happen during testing or unusual scenarios
                logger.warning("No running event loop found, creating a new one")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Get Redis URL from environment or use default
            redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
            if not redis_url:
                logger.error("Redis URL not configured")
                yield None
                return
                
            # Connect to Redis with modern from_url method
            client = await redis.asyncio.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=3.0,  # Short timeout for serverless
                socket_connect_timeout=2.0,
                retry_on_timeout=True
            )
            
            try:
                # Validate connection with ping
                await client.ping()
                # Connection is valid, yield it to the caller
                yield client
            except Exception as e:
                # Connection failed validation
                logger.error(f"Redis connection validation failed: {e}")
                if client:
                    try:
                        await client.close()
                    except Exception as ex:
                        logger.warning(f"Error closing invalid Redis connection: {ex}")
                    client = None
                yield None
        except Exception as e:
            logger.error(f"Event loop error: {e}")
            yield None
            
    except Exception as e:
        # Connection creation failed
        logger.error(f"Error creating Redis connection: {e}")
        yield None
    finally:
        # Always ensure the connection is properly closed
        if client:
            try:
                await client.close()
            except Exception as e:
                # Log but don't re-raise - we don't want cleanup errors to propagate
                logger.warning(f"Error closing Redis connection: {e}")

async def test_redis_connection() -> bool:
    """Test that Redis connection is working."""
    try:
        async with redis_connection() as client:
            return client is not None
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False

# Thread state functions
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the state for a thread with improved error handling."""
    if not thread_id:
        logger.warning("get_thread_state called with empty thread_id")
        return None
        
    key = f"thread_state:{thread_id}"
    
    # Try Redis first with better error handling
    try:
        async with redis_connection() as client:
            if client:
                try:
                    value = await client.get(key)
                    if value:
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding JSON for {key}: {e}")
                            return None
                except Exception as inner_e:
                    logger.warning(f"Redis operation error for {key}: {inner_e}")
            else:
                logger.warning(f"Redis client not available for {key}")
    except Exception as e:
        logger.warning(f"Redis connection error for {key}: {e}")
    
    # Fall back to memory cache
    try:
        if key in _memory_cache:
            logger.info(f"Using memory cache fallback for {key}")
            return _memory_cache.get(key)
    except Exception as cache_e:
        logger.error(f"Memory cache error for {key}: {cache_e}")
    
    return None

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save the state for a thread with improved error handling."""
    if not thread_id:
        logger.warning("save_thread_state called with empty thread_id")
        return False
        
    if not state:
        logger.warning(f"save_thread_state called with empty state for thread {thread_id}")
        return False
        
    key = f"thread_state:{thread_id}"
    
    # Create a copy of the state for serialization
    serializable_state = state.copy()
    
    # Convert LangChain message objects to dictionaries
    if "messages" in serializable_state and isinstance(serializable_state["messages"], list):
        serializable_messages = []
        for msg in serializable_state["messages"]:
            if hasattr(msg, "content") and hasattr(msg, "type"):
                # LangChain message objects
                serializable_messages.append({
                    "type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "content": msg.content,
                    "additional_kwargs": getattr(msg, "additional_kwargs", {})
                })
            elif isinstance(msg, dict):
                serializable_messages.append(msg)
            else:
                logger.warning(f"Unknown message type: {type(msg)}")
        serializable_state["messages"] = serializable_messages
    
    # Convert value to JSON with better error handling
    try:
        value = json.dumps(serializable_state, default=str)  # Use default=str to handle non-serializable objects
    except Exception as e:
        logger.error(f"Error serializing state for {key}: {e}")
        
        # Try with a simpler approach - just keep essential data
        try:
            # Extract just the essential data
            simplified_state = {
                "thread_id": thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": state.get("context", {})
            }
            value = json.dumps(simplified_state)
            logger.info(f"Created simplified state for {thread_id}")
        except Exception as e2:
            logger.error(f"Error creating simplified state for {key}: {e2}")
            return False
    
    # Try Redis first with better error handling
    redis_success = False
    try:
        async with redis_connection() as client:
            if client:
                try:
                    await client.set(key, value, ex=86400)  # 24 hour expiration
                    redis_success = True
                    logger.info(f"Successfully saved thread state to Redis: {thread_id}")
                except Exception as inner_e:
                    logger.warning(f"Redis operation error for {key}: {inner_e}")
            else:
                logger.warning(f"Redis client not available for {key}")
    except Exception as e:
        logger.warning(f"Redis connection error for {key}: {e}")
    
    # Always update memory cache (regardless of Redis success)
    try:
        try:
            _memory_cache[key] = json.loads(value)
        except json.JSONDecodeError:
            _memory_cache[key] = value
            
        logger.info(f"Stored {key} in memory cache fallback")
        return True
    except Exception as e:
        logger.error(f"Error setting {key} in memory cache: {e}")
        return redis_success  # Return Redis result if memory cache fails

# Import custom modules
try:
    from backend.api.thread_summary import thread_summary_fallback
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
    from backend.api.debug_openai import router as debug_openai_router
    logger.info("Successfully imported debug_openai module")
except Exception as e:
    logger.error(f"Failed to import debug_openai module: {str(e)}")

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

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses"""
    request_id = str(uuid.uuid4())
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    # Log request headers
    headers = dict(request.headers)
    logger.info(f"Request {request_id} headers: {headers}")
    
    # Try to log request body for POST requests
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            # Store the body content for later use
            request._body = body
            if body:
                try:
                    # Try to parse as JSON
                    body_str = body.decode()
                    json_body = json.loads(body_str)
                    logger.info(f"Request {request_id} body (JSON): {json_body}")
                except:
                    # Log as raw string if not JSON
                    logger.info(f"Request {request_id} body (raw): {body}")
        except Exception as e:
            logger.error(f"Error reading request body: {e}")
    
    try:
        # Process the request
        response = await call_next(request)
        logger.info(f"Request {request_id} completed: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request {request_id} failed with error: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e)}
        )

# Define request/response models directly
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    language: Optional[str] = "en"
    local_event_id: Optional[str] = None
    timezone: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    user_context: Optional[Dict[str, Any]] = None
    reset_context: bool = False

class ChatResponse(BaseModel):
    response: str
    command_processed: bool = False
    command_type: Optional[str] = None
    command_data: Optional[Dict[str, Any]] = None

# Import message types with fallbacks
try:
    from backend.models.message_types import HumanMessage, AIMessage
    logger.info("Imported message types from backend.models.message_types")
except ImportError:
    try:
        from langchain_core.messages import HumanMessage, AIMessage
        logger.info("Imported message types from langchain_core.messages")
    except ImportError:
        logger.warning("Could not import standard message types, using custom implementation")
        # Define fallback message classes
        class HumanMessage:
            def __init__(self, content):
                self.content = content
                self.type = "human"
                
        class AIMessage:
            def __init__(self, content):
                self.content = content
                self.type = "ai"

# Direct implementation of chat endpoints
@app.post("/api/chat")
async def chat(chat_request: ChatRequest):
    """
    Process a chat request and return a response.
    Enhanced with timeout protection for serverless environments.
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now()
    logger.info(f"Request {request_id} started: POST /api/chat")
    
    try:
        # Log request details for debugging
        try:
            logger.info(f"Request {request_id} payload: {chat_request.model_dump_json()}")
        except Exception as e:
            logger.warning(f"Could not log request payload: {str(e)}")
            logger.info(f"Request {request_id} message: {chat_request.message}")
        
        # Set up a timeout for the entire operation - Vercel has 30s limit
        # We'll use 25s to give some buffer for response handling
        async def process_with_timeout():
            # Get thread ID from request or generate a new one
            thread_id = chat_request.thread_id
            if not thread_id:
                thread_id = f"thread_{uuid.uuid4().hex[:12]}"
                logger.info(f"Generated new thread ID: {thread_id}")
                
            # Call the process_chat function
            from backend.api.chat import process_chat
            result = await process_chat(
                message_text=chat_request.message,
                thread_id=thread_id,
                language=chat_request.language or "en"
            )
            
            logger.info(f"process_chat result: {result}")
            
            if not result.get("processed", False):
                logger.error("Message processing failed")
                return {
                    "response": result.get("message", "I'm sorry, I encountered an error processing your request. Please try again."),
                    "thread_id": thread_id
                }
                
            return {
                "response": result.get("message", ""),
                "thread_id": thread_id
            }

        # Run the processing with a timeout
        try:
            result = await asyncio.wait_for(process_with_timeout(), timeout=25.0)
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Request {request_id} processed in {processing_time:.2f}s")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Request {request_id} timed out after 25 seconds")
            return {
                "response": "I'm sorry, but your request took too long to process. Please try a shorter or simpler message.",
                "thread_id": chat_request.thread_id or f"thread_{uuid.uuid4().hex[:12]}"
            }
    except Exception as e:
        logger.exception(f"Error processing chat request: {e}")
        return {
            "response": "I'm sorry, I encountered an error processing your request. Please try again.",
            "thread_id": chat_request.thread_id or f"thread_{uuid.uuid4().hex[:12]}"
        }

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
                    # Check if it's already a dict or a message object
                    if isinstance(msg, dict):
                        msg_type = "human" if msg.get("type") == "human" else "ai"
                        messages.append({
                            "content": msg.get("content", ""),
                            "type": msg_type
                        })
                    else:
                        # It's a message object
                        msg_type = "human" if hasattr(msg, "type") and msg.type == "human" else "ai"
                        messages.append({
                            "content": getattr(msg, "content", ""),
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
                    "status": "success"
                })
                
        except Exception as e:
            logger.error(f"Error using backend context implementation: {str(e)}")
            logger.error(traceback.format_exc())
            
            return JSONResponse({
                "thread_id": thread_id, 
                "messages": [],
                "status": "error",
                "error": f"Failed to retrieve context: {str(e)}"
            })
    except Exception as e:
        logger.error(f"Error in direct context endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse({
            "thread_id": thread_id,
            "messages": [],
            "status": "error",
            "error": f"Failed to process request: {str(e)}"
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
            
            # Extract event data from request body
            thread_id = body.get("thread_id")
            event_type = body.get("event_type")
            
            # Map start_time to event_time (the field expected by routine_db)
            event_time = body.get("start_time")
            if not event_time:
                event_time = body.get("event_time")  # Fallback to event_time if provided
                
            # Prepare event_data from notes field if present
            event_data = body.get("event_data", {})
            if not event_data and "notes" in body:
                event_data = {"notes": body.get("notes")}
                
            # Get local_id if present
            local_id = body.get("local_id")
            
            # Log the parameters being passed to add_event
            logger.info(f"Calling add_event with: thread_id={thread_id}, event_type={event_type}, event_time={event_time}")
            
            event = await routine_db.add_event(
                thread_id=thread_id,
                event_type=event_type,
                event_time=event_time,
                event_data=event_data,
                local_id=local_id
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

# Direct implementation of get_routine_summary
async def _get_summary(thread_id: str, period: str = "day", force_refresh: bool = True) -> Dict[str, Any]:
    """
    Enhanced implementation of the get summary endpoint with isolated Redis operations and timeout handling.
    """
    start_time = datetime.now()
    logger.info(f"Getting summary for thread: {thread_id}, period: {period}, force_refresh: {force_refresh}")
    
    try:
        # Set up a timeout for the summary generation
        summary_timeout = 25.0  # 25 seconds - vercel functions have 30s max

        # Calculate time range based on period
        now = datetime.now(timezone.utc)
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "Today"
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "This Week"
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_name = "This Month"
        else:
            # Default to last 24 hours if period is unknown
            start_date = now - timedelta(days=1)
            period_name = "Last 24 Hours"
        
        # Create an empty summary structure
        empty_summary = {
            "period": period,
            "period_name": period_name,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "thread_id": thread_id,
            "routines": {
                "sleep": {
                    "total_events": 0,
                    "total_duration": 0,
                    "average_duration": 0,
                    "latest_event": None,
                    "events": []
                },
                "feeding": {
                    "total_events": 0,
                    "latest_event": None,
                    "events": []
                }
            }
        }
        
        # Try to use the backend implementation if available
        try:
            import backend.db.routine_db as routine_db
            
            # Use asyncio.wait_for to enforce a timeout
            try:
                logger.info(f"Calling routine_db.get_summary for thread {thread_id}")
                summary = await asyncio.wait_for(
                    routine_db.get_summary(thread_id, period, force_refresh),
                    timeout=summary_timeout
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Generated summary for thread {thread_id} in {execution_time:.2f}s")
                
                # Log the summary for debugging
                summary_str = json.dumps(summary, default=str)
                logger.info(f"Summary result (truncated): {summary_str[:500]}...")
                
                if summary:
                    # Ensure the structure is correct
                    if "routines" not in summary:
                        logger.warning(f"Summary missing routines key, adding empty structure")
                        summary["routines"] = empty_summary["routines"]
                    
                    # Ensure sleep and feeding structures exist
                    if "sleep" not in summary["routines"]:
                        logger.warning(f"Summary missing sleep data, adding empty structure")
                        summary["routines"]["sleep"] = empty_summary["routines"]["sleep"]
                        
                    if "feeding" not in summary["routines"]:
                        logger.warning(f"Summary missing feeding data, adding empty structure")
                        summary["routines"]["feeding"] = empty_summary["routines"]["feeding"]
                        
                    return summary
                    
            except asyncio.TimeoutError:
                logger.error(f"Summary generation timed out after {summary_timeout}s for thread {thread_id}")
                return {
                    **empty_summary,
                    "error": f"Summary generation timed out after {summary_timeout}s"
                }
            
            return empty_summary
                
        except ImportError:
            logger.warning("Could not import routine_db module, using fallback implementation")
            return empty_summary
            
        except Exception as e:
            logger.error(f"Error using backend get summary implementation: {str(e)}")
            logger.error(traceback.format_exc())
            return empty_summary
            
    except Exception as e:
        logger.error(f"Error in get_summary: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Return a fallback response
        return {
            "period": period,
            "error": str(e),
            "thread_id": thread_id,
            "routines": {
                "sleep": {
                    "total_events": 0,
                    "total_duration": 0,
                    "average_duration": 0,
                    "latest_event": None,
                    "events": []
                },
                "feeding": {
                    "total_events": 0,
                    "latest_event": None,
                    "events": []
                }
            }
        }

@app.get("/api/routines/summary/{thread_id}")
async def direct_get_summary(thread_id: str, period: str = "day", force_refresh: bool = True):
    """
    Direct implementation of the get summary endpoint to bypass import issues.
    Always forces a refresh by default to ensure we get the latest data.
    """
    logger.info(f"Direct get summary endpoint called for thread: {thread_id}, period: {period}, force_refresh: {force_refresh}")
    
    try:
        summary = await _get_summary(thread_id, period, force_refresh)
        
        return JSONResponse({
            "summary": summary,
            "status": "success"
        })
            
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

# Health check with safe event loop access
@app.get("/api/health")
async def health_check():
    """
    Enhanced health check endpoint that tests all service components
    """
    start_time = datetime.now()
    logger.info("Health check endpoint called")
    
    try:
        # Now we can safely access the event loop inside an async function
        event_loop = asyncio.get_running_loop()
        logger.info(f"Health check running in event loop: {event_loop}")
        
        # Test results
        results = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {},
            "environment": {
                "vercel": os.environ.get('VERCEL', '0') == '1' or os.path.exists('/.vercel'),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "event_loop": str(event_loop),
                "serverless": os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None or os.environ.get('VERCEL', '0') == '1'
            }
        }
        
        # Check Redis connection
        try:
            # Use the new diagnostics function for detailed Redis information
            redis_diagnostics = await get_redis_diagnostics()
            
            # Provide detailed Redis information
            results["services"]["redis"] = redis_diagnostics
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            logger.exception("Redis diagnostics error:")
            results["services"]["redis"] = {
                "status": "error", 
                "error": str(e),
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check thread state access
        try:
            test_thread_id = "health-check-thread"
            test_data = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test write
            save_result = await save_thread_state(test_thread_id, test_data)
            
            # Test read
            read_result = await get_thread_state(test_thread_id)
            
            results["services"]["thread_state"] = {
                "status": "working" if save_result and read_result and read_result.get("test") is True else "failing",
                "write_success": bool(save_result),
                "read_success": bool(read_result)
            }
        except Exception as e:
            logger.error(f"Thread state health check failed: {e}")
            results["services"]["thread_state"] = {
                "status": "error", 
                "error": str(e),
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check if backend modules are available
        backend_available = False
        try:
            import backend.workflow.workflow
            import backend.services.redis_service
            backend_available = True
            results["backend_available"] = backend_available
        except Exception as e:
            logger.error(f"Backend modules not available: {str(e)}")
            results["backend_available"] = False
            results["backend_error"] = str(e)
        
        # Overall status determination
        service_statuses = [s.get("status") for s in results["services"].values()]
        if any(status == "error" for status in service_statuses):
            results["status"] = "error"
        elif any(status in ["disconnected", "failing", "uninitialized"] for status in service_statuses):
            results["status"] = "degraded"
        else:
            results["status"] = "ok"
        
        # Performance metrics
        process_time = (datetime.now() - start_time).total_seconds()
        results["performance"] = {
            "health_check_duration_seconds": process_time
        }
        
        return JSONResponse(results)
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Health check failed: {str(e)} after {process_time:.3f}s")
        logger.error(traceback.format_exc())
        
        return JSONResponse({
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc().split("\n")[-10:],
            "duration_seconds": process_time
        }, status_code=500)

# Diagnostics with safe event loop access
@app.get("/api/diagnostics")
async def diagnostics():
    """
    Diagnostic endpoint to help troubleshoot deployment issues.
    Returns detailed information about the running environment.
    """
    logger.info("Diagnostics endpoint called")
    
    try:
        # Safely access event loop inside async function
        event_loop = asyncio.get_running_loop()
        logger.info(f"Diagnostics running in event loop: {event_loop}")
        
        # Basic environment info
        env_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version,
            "python_path": sys.path,
            "environment_variables": {k: "***" if k.lower() in ("openai_api_key", "storage_url") else v 
                                        for k, v in os.environ.items()},
            "current_directory": os.getcwd(),
            "file_location": __file__,
            "event_loop": str(event_loop),
            "vercel": os.environ.get('VERCEL', '0') == '1' or os.path.exists('/.vercel'),
            "serverless": os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None or os.environ.get('VERCEL', '0') == '1'
        }
        
        # Redis test
        redis_info = {}
        try:
            # Test connection
            redis_connected = await test_redis_connection()
            redis_info["connected"] = redis_connected
            
            # Test thread state
            if redis_connected:
                test_thread_id = "diagnostics-test"
                test_data = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
                
                # Test write
                save_result = await save_thread_state(test_thread_id, test_data)
                redis_info["save_result"] = save_result
                
                # Test read
                read_result = await get_thread_state(test_thread_id)
                redis_info["read_result"] = read_result is not None
                redis_info["read_data_valid"] = read_result and read_result.get("test") is True
                
        except Exception as e:
            redis_info["error"] = str(e)
            redis_info["traceback"] = traceback.format_exc().split("\n")
        
        # Module availability
        modules_info = {}
        try:
            # FastAPI and web modules
            modules_info["fastapi"] = {"version": fastapi.__version__, "location": fastapi.__file__}
            modules_info["pydantic"] = {"version": pydantic.__version__, "location": pydantic.__file__}
            modules_info["starlette"] = {"version": starlette.__version__, "location": starlette.__file__}
            
            # Redis modules
            modules_info["redis"] = {"version": redis.__version__, "location": redis.__file__}
            modules_info["redis.asyncio"] = {"available": True, "location": redis.asyncio.__file__}
            
            # Check for key backend modules
            try:
                import backend.workflow.workflow
                modules_info["workflow"] = {"available": True, "location": backend.workflow.workflow.__file__}
            except ImportError:
                modules_info["workflow"] = {"available": False, "error": "Module not found"}
                
            try:
                import backend.services.redis_service
                modules_info["redis_service"] = {"available": True, "location": backend.services.redis_service.__file__}
            except ImportError:
                modules_info["redis_service"] = {"available": False, "error": "Module not found"}
                
            try:
                import backend.db.routine_db
                modules_info["routine_db"] = {"available": True, "location": backend.db.routine_db.__file__}
            except ImportError:
                modules_info["routine_db"] = {"available": False, "error": "Module not found"}
                
        except Exception as e:
            modules_info["error"] = str(e)
            modules_info["traceback"] = traceback.format_exc().split("\n")
            
        # Put everything together
        result = {
            "environment": env_info,
            "redis": redis_info,
            "modules": modules_info
        }
        
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Diagnostics endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc().split("\n")
        }, status_code=500)

async def get_workflow():
    """Get or create the workflow for processing messages"""
    try:
        from backend.workflow.workflow import create_workflow
        logger.info("Creating workflow using imported create_workflow function")
        
        try:
            # Need to await create_workflow since it's an async function
            workflow = await create_workflow()
            logger.info("Successfully created workflow from imported function")
            return workflow
        except Exception as e:
            logger.error(f"Error with imported create_workflow: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create a simple sequential workflow directly instead
            from backend.workflow.workflow import WorkflowInvoker
            from backend.workflow.extract_context import extract_context
            from backend.workflow.select_domain import select_domain  
            from backend.workflow.generate_response import generate_response
            from backend.workflow.post_process import post_process
            
            logger.info("Creating direct workflow implementation")
            
            # Define a simple sequential workflow function that doesn't rely on async/await syntax
            async def simple_workflow_runner(state):
                try:
                    # Log the input state
                    logger.info(f"Processing workflow with {len(state.get('messages', []))} messages")
                    
                    # Make a copy of the state to avoid modifying the original
                    current_state = state.copy()
                    
                    # Store original context to prevent accidental loss
                    import copy
                    original_context = copy.deepcopy(current_state.get("context", {}))
                    original_user_context = copy.deepcopy(current_state.get("user_context", {}))
                    
                    # Extract context
                    logger.info("Running extract_context")
                    try:
                        current_state = await extract_context(current_state)
                    except Exception as e:
                        logger.error(f"Error in extract_context: {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    # Select domain
                    logger.info("Running select_domain")
                    try:
                        current_state = await select_domain(current_state)
                    except Exception as e:
                        logger.error(f"Error in select_domain: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Set a default domain if there's an error
                        current_state["domain"] = "general"
                    
                    # Generate response
                    logger.info("Running generate_response")
                    try:
                        current_state = await generate_response(current_state)
                    except Exception as e:
                        logger.error(f"Error in generate_response: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Add a fallback response if there's an error
                        try:
                            current_state["messages"].append(AIMessage(content="I apologize, but I encountered an error generating a response. Could you please try again?"))
                        except Exception as msg_error:
                            logger.error(f"Error adding message: {str(msg_error)}")
                            # Use a dict as fallback
                            current_state["messages"].append({"type": "ai", "content": "I apologize, but I encountered an error generating a response. Could you please try again?"})
                    
                    # Post-process
                    logger.info("Running post_process")
                    try:
                        current_state = await post_process(current_state)
                    except Exception as e:
                        logger.error(f"Error in post_process: {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    # Check if context was lost during processing and restore it
                    if not current_state.get("context") and original_context:
                        logger.warning("Context was lost during processing, restoring from backup")
                        current_state["context"] = original_context
                        
                    if not current_state.get("user_context") and original_user_context:
                        logger.warning("User context was lost during processing, restoring from backup")
                        current_state["user_context"] = original_user_context
                    
                    logger.info("Workflow execution completed successfully")
                    return current_state
                except Exception as e:
                    logger.error(f"Error in workflow execution: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Ensure we have a valid state to return
                    if "messages" not in state:
                        state["messages"] = []
                        
                    # Add a fallback error message
                    try:
                        state["messages"].append(AIMessage(content="I apologize, but I encountered an error processing your message. Please try again."))
                    except Exception as msg_error:
                        logger.error(f"Error adding message: {str(msg_error)}")
                        # Use a dict as fallback
                        state["messages"].append({"type": "ai", "content": "I apologize, but I encountered an error processing your message. Please try again."})
                    
                    return state
            
            # Return a workflow invoker with our simple runner
            return WorkflowInvoker(simple_workflow_runner)
            
        except Exception as e:
            logger.error(f"Error creating direct workflow: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    except Exception as e:
        logger.error(f"Error creating workflow: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Fallback to a simple workflow if the import fails
        try:
            from backend.workflow.workflow import WorkflowInvoker
            from backend.workflow.extract_context import extract_context
            from backend.workflow.select_domain import select_domain
            from backend.workflow.generate_response import generate_response
            from backend.workflow.post_process import post_process
            
            logger.info("Creating fallback workflow")
            
            # Create a simple sequential workflow
            async def simple_workflow(state):
                try:
                    # Extract context
                    state = await extract_context(state)
                    
                    # Select domain
                    state = await select_domain(state)
                    
                    # Generate response
                    state = await generate_response(state)
                    
                    # Post-process
                    state = await post_process(state)
                    
                    return state
                except Exception as workflow_error:
                    logger.error(f"Error in simple workflow: {str(workflow_error)}")
                    logger.error(traceback.format_exc())
                    
                    # Return the original state with an error message
                    if "messages" not in state:
                        state["messages"] = []
                    
                    # Import at the function level to avoid circular imports
                    try:
                        from backend.models.message_types import AIMessage
                    except ImportError:
                        # If we can't import from our models, try langchain
                        try:
                            from langchain_core.messages import AIMessage
                        except ImportError:
                            # Define a simple message class as last resort
                            class AIMessage:
                                def __init__(self, content):
                                    self.content = content
                                    self.type = "ai"
                    
                    state["messages"].append(AIMessage(content="I apologize, but I encountered an error processing your message. Please try again."))
                    return state
            
            return WorkflowInvoker(simple_workflow)
        except Exception as fallback_error:
            logger.error(f"Failed to create fallback workflow: {str(fallback_error)}")
            logger.error(traceback.format_exc())
            
            # Return an extremely simple workflow as last resort
            class EmergencyWorkflow:
                async def invoke(self, state):
                    if "messages" not in state:
                        state["messages"] = []
                    
                    logger.error("Using EMERGENCY workflow due to critical errors in workflow creation")
                    logger.error("This indicates a serious issue with the application configuration")
                    
                    # Define AIMessage class directly without imports
                    class LocalAIMessage:
                        def __init__(self, content):
                            self.content = content
                            self.type = "ai"
                    
                    error_response = (
                        "I'm sorry, but I'm experiencing technical difficulties at the moment. "
                        "Our team has been automatically notified and is working on a fix. "
                        "Please try again in a few minutes, or contact support if the issue persists."
                    )
                    
                    # Create a properly formatted message with detailed diagnostic info
                    try:
                        # Create a basic timestamp for debugging
                        import time
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Add metadata about the error if available
                        if "metadata" not in state:
                            state["metadata"] = {}
                        
                        state["metadata"]["error_type"] = "emergency_workflow"
                        state["metadata"]["error_time"] = timestamp
                        state["metadata"]["command_processed"] = False
                        
                        # Add the response message
                        state["messages"].append(LocalAIMessage(content=error_response))
                        
                        logger.info(f"Emergency workflow returned response at {timestamp}")
                    except Exception as final_error:
                        logger.critical(f"Critical error in emergency response: {str(final_error)}")
                        # Last resort - use a dict
                        state["messages"].append({"type": "ai", "content": error_response})
                    
                    return state
            
            return EmergencyWorkflow()

@app.get("/api/warmup")
async def warmup():
    """
    Warmup endpoint to reduce cold start impact.
    This loads key components but doesn't execute expensive operations.
    """
    logger.info("Warmup endpoint called")
    
    try:
        # Test Redis connection (lightweight operation)
        redis_available = await test_redis_connection()
        
        # Pre-initialize workflow (but don't run it)
        _ = await get_workflow()
        
        # Return status
        return JSONResponse({
            "status": "ready",
            "redis_available": redis_available,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error during warmup: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)
