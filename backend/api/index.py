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

def validate_environment():
    """
    Validate that all required environment variables are set.
    This runs during startup to catch configuration issues early.
    """
    required_vars = ["OPENAI_API_KEY", "STORAGE_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        # Don't fail startup, but log an error
        return False
    
    # Validate Redis URL format
    redis_url = os.environ.get("STORAGE_URL", "")
    if not redis_url.startswith(("redis://", "rediss://")):
        logger.error(f"Invalid STORAGE_URL format. Must start with redis:// or rediss://")
        return False
        
    logger.info("Environment validation passed")
    return True

# Run environment validation during module initialization
env_valid = validate_environment()

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
    start_time = datetime.now()
    client = None
    connection_id = str(uuid.uuid4())[:8]  # Generate a unique ID for this connection attempt
    logger.info(f"[REDIS:{connection_id}] Connection attempt started")
    
    try:
        # Ensure we have an event loop - in serverless environments, this might
        # not be available during module initialization, but should be during request handling
        try:
            # Get the current event loop or create a new one if none exists
            try:
                loop = asyncio.get_running_loop()
                logger.debug(f"[REDIS:{connection_id}] Got existing event loop: {id(loop)}")
            except RuntimeError:
                # No running event loop, create a new one if none exists
                # This should only happen during testing or unusual scenarios
                logger.warning(f"[REDIS:{connection_id}] No running event loop found, creating a new one")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Get Redis URL from environment or use default
            redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
            if not redis_url:
                logger.error(f"[REDIS:{connection_id}] Redis URL not configured")
                yield None
                return
                
            logger.debug(f"[REDIS:{connection_id}] Connecting to Redis at {redis_url.split('@')[0]}@...")
            
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
                ping_start = datetime.now()
                await client.ping()
                ping_duration = (datetime.now() - ping_start).total_seconds()
                logger.info(f"[REDIS:{connection_id}] Connection established and validated with ping in {ping_duration:.3f}s")
                # Connection is valid, yield it to the caller
                yield client
            except Exception as e:
                # Connection failed validation
                logger.error(f"[REDIS:{connection_id}] Redis connection validation failed: {e}")
                if client:
                    try:
                        await client.close()
                        logger.debug(f"[REDIS:{connection_id}] Closed invalid connection after ping failure")
                    except Exception as ex:
                        logger.warning(f"[REDIS:{connection_id}] Error closing invalid Redis connection: {ex}")
                    client = None
                yield None
        except Exception as e:
            logger.error(f"[REDIS:{connection_id}] Event loop error: {e}")
            yield None
            
    except Exception as e:
        # Connection creation failed
        logger.error(f"[REDIS:{connection_id}] Error creating Redis connection: {e}")
        yield None
    finally:
        # Always ensure the connection is properly closed
        if client:
            try:
                await client.close()
                total_duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"[REDIS:{connection_id}] Connection closed after {total_duration:.3f}s")
            except Exception as e:
                # Log but don't re-raise - we don't want cleanup errors to propagate
                logger.warning(f"[REDIS:{connection_id}] Error closing Redis connection: {e}")
        else:
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"[REDIS:{connection_id}] Connection attempt finished in {total_duration:.3f}s (no client created)")

async def test_redis_connection() -> bool:
    """Test that Redis connection is working."""
    conn_start = datetime.now()
    connection_id = str(uuid.uuid4())[:8]
    logger.info(f"[REDIS-TEST:{connection_id}] Testing Redis connection")
    
    try:
        async with redis_connection() as client:
            result = client is not None
            duration = (datetime.now() - conn_start).total_seconds()
            if result:
                logger.info(f"[REDIS-TEST:{connection_id}] Connection test successful in {duration:.3f}s")
            else:
                logger.error(f"[REDIS-TEST:{connection_id}] Connection test failed in {duration:.3f}s - client is None")
            return result
    except Exception as e:
        duration = (datetime.now() - conn_start).total_seconds()
        logger.error(f"[REDIS-TEST:{connection_id}] Connection test failed with exception in {duration:.3f}s: {e}")
        logger.error(traceback.format_exc())
        return False

# Thread state functions
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the state for a thread with improved error handling."""
    start_time = datetime.now()
    operation_id = str(uuid.uuid4())[:8]
    
    if not thread_id:
        logger.warning(f"[STATE-GET:{operation_id}] Called with empty thread_id")
        return None
        
    key = f"thread_state:{thread_id}"
    logger.info(f"[STATE-GET:{operation_id}] Retrieving state for thread {thread_id}")
    
    # Try Redis first with better error handling
    try:
        logger.debug(f"[STATE-GET:{operation_id}] Attempting to get state from Redis")
        async with redis_connection() as client:
            if client:
                try:
                    redis_start = datetime.now()
                    value = await client.get(key)
                    redis_duration = (datetime.now() - redis_start).total_seconds()
                    
                    if value:
                        logger.debug(f"[STATE-GET:{operation_id}] Got value from Redis in {redis_duration:.3f}s, length: {len(value)}")
                        try:
                            result = json.loads(value)
                            total_duration = (datetime.now() - start_time).total_seconds()
                            logger.info(f"[STATE-GET:{operation_id}] Successfully retrieved and parsed state in {total_duration:.3f}s")
                            return result
                        except json.JSONDecodeError as e:
                            logger.error(f"[STATE-GET:{operation_id}] Error decoding JSON for {key}: {e}")
                            return None
                    else:
                        logger.info(f"[STATE-GET:{operation_id}] No value found in Redis for {key} (took {redis_duration:.3f}s)")
                except Exception as inner_e:
                    logger.warning(f"[STATE-GET:{operation_id}] Redis operation error for {key}: {inner_e}")
            else:
                logger.warning(f"[STATE-GET:{operation_id}] Redis client not available for {key}")
    except Exception as e:
        logger.warning(f"[STATE-GET:{operation_id}] Redis connection error for {key}: {e}")
    
    # Fall back to memory cache
    try:
        cache_start = datetime.now()
        if key in _memory_cache:
            cache_duration = (datetime.now() - cache_start).total_seconds()
            logger.info(f"[STATE-GET:{operation_id}] Using memory cache fallback for {key} (took {cache_duration:.3f}s)")
            result = _memory_cache.get(key)
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[STATE-GET:{operation_id}] Retrieved state from memory cache in {total_duration:.3f}s")
            return result
        else:
            logger.info(f"[STATE-GET:{operation_id}] Key not found in memory cache")
    except Exception as cache_e:
        logger.error(f"[STATE-GET:{operation_id}] Memory cache error for {key}: {cache_e}")
    
    total_duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"[STATE-GET:{operation_id}] Failed to get state for {key} in {total_duration:.3f}s")
    return None

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save the state for a thread with improved error handling."""
    start_time = datetime.now()
    operation_id = str(uuid.uuid4())[:8]
    
    if not thread_id:
        logger.warning(f"[STATE-SAVE:{operation_id}] Called with empty thread_id")
        return False
        
    if not state:
        logger.warning(f"[STATE-SAVE:{operation_id}] Called with empty state for thread {thread_id}")
        return False
        
    key = f"thread_state:{thread_id}"
    logger.info(f"[STATE-SAVE:{operation_id}] Saving state for thread {thread_id}, state keys: {list(state.keys())}")
    
    # Create a copy of the state for serialization
    serializable_state = state.copy()
    
    # Convert LangChain message objects to dictionaries
    if "messages" in serializable_state and isinstance(serializable_state["messages"], list):
        msg_start = datetime.now()
        serializable_messages = []
        msg_count = len(serializable_state["messages"])
        logger.debug(f"[STATE-SAVE:{operation_id}] Converting {msg_count} messages to serializable format")
        
        for idx, msg in enumerate(serializable_state["messages"]):
            try:
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
                    logger.warning(f"[STATE-SAVE:{operation_id}] Unknown message type at index {idx}: {type(msg)}")
            except Exception as msg_error:
                logger.error(f"[STATE-SAVE:{operation_id}] Error converting message {idx}: {msg_error}")
                
        serializable_state["messages"] = serializable_messages
        msg_duration = (datetime.now() - msg_start).total_seconds()
        logger.debug(f"[STATE-SAVE:{operation_id}] Converted {msg_count} messages in {msg_duration:.3f}s")
    
    # Convert value to JSON with better error handling
    json_start = datetime.now()
    try:
        value = json.dumps(serializable_state, default=str)  # Use default=str to handle non-serializable objects
        json_duration = (datetime.now() - json_start).total_seconds()
        logger.debug(f"[STATE-SAVE:{operation_id}] Serialized state to JSON in {json_duration:.3f}s, size: {len(value)} bytes")
    except Exception as e:
        logger.error(f"[STATE-SAVE:{operation_id}] Error serializing state for {key}: {e}")
        
        # Try with a simpler approach - just keep essential data
        try:
            # Extract just the essential data
            simplified_state = {
                "thread_id": thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": state.get("context", {})
            }
            value = json.dumps(simplified_state)
            logger.info(f"[STATE-SAVE:{operation_id}] Created simplified state for {thread_id}")
        except Exception as e2:
            logger.error(f"[STATE-SAVE:{operation_id}] Error creating simplified state for {key}: {e2}")
            return False
    
    # Try Redis first with better error handling
    redis_success = False
    redis_start = datetime.now()
    try:
        async with redis_connection() as client:
            if client:
                try:
                    await client.set(key, value, ex=86400)  # 24 hour expiration
                    redis_duration = (datetime.now() - redis_start).total_seconds()
                    redis_success = True
                    logger.info(f"[STATE-SAVE:{operation_id}] Successfully saved thread state to Redis in {redis_duration:.3f}s")
                except Exception as inner_e:
                    logger.warning(f"[STATE-SAVE:{operation_id}] Redis operation error for {key}: {inner_e}")
            else:
                logger.warning(f"[STATE-SAVE:{operation_id}] Redis client not available for {key}")
    except Exception as e:
        logger.warning(f"[STATE-SAVE:{operation_id}] Redis connection error for {key}: {e}")
    
    # Always update memory cache (regardless of Redis success)
    try:
        cache_start = datetime.now()
        try:
            _memory_cache[key] = json.loads(value)
        except json.JSONDecodeError:
            _memory_cache[key] = value
            
        cache_duration = (datetime.now() - cache_start).total_seconds()
        logger.info(f"[STATE-SAVE:{operation_id}] Stored {key} in memory cache in {cache_duration:.3f}s")
        
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[STATE-SAVE:{operation_id}] Total save operation completed in {total_duration:.3f}s")
        return True
    except Exception as e:
        logger.error(f"[STATE-SAVE:{operation_id}] Error setting {key} in memory cache: {e}")
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"[STATE-SAVE:{operation_id}] Save operation failed in {total_duration:.3f}s")
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
    logger.info(f"[CHAT:{request_id}] Request started: POST /api/chat")
    
    try:
        # Log request details for debugging
        try:
            thread_id = chat_request.thread_id or f"new_thread_{uuid.uuid4().hex[:8]}"
            language = chat_request.language or "en"
            message_length = len(chat_request.message) if chat_request.message else 0
            
            logger.info(f"[CHAT:{request_id}] Request details: thread_id={thread_id}, language={language}, message_length={message_length}")
            
            if chat_request.timezone:
                logger.info(f"[CHAT:{request_id}] Timezone specified: {chat_request.timezone}")
                
            if chat_request.reset_context:
                logger.info(f"[CHAT:{request_id}] Context reset requested")
                
            if chat_request.context:
                context_keys = list(chat_request.context.keys())
                logger.info(f"[CHAT:{request_id}] Context provided with keys: {context_keys}")
        except Exception as e:
            logger.warning(f"[CHAT:{request_id}] Could not log request payload: {str(e)}")
            logger.info(f"[CHAT:{request_id}] Raw message: {chat_request.message[:100]}...")
        
        # Set up a timeout for the entire operation - Vercel has 30s limit
        # We'll use 25s to give some buffer for response handling
        async def process_with_timeout():
            # Get thread ID from request or generate a new one
            thread_id = chat_request.thread_id
            if not thread_id:
                thread_id = f"thread_{uuid.uuid4().hex[:12]}"
                logger.info(f"[CHAT:{request_id}] Generated new thread ID: {thread_id}")
                
            process_start = datetime.now()
            try:
                # If direct processing is available, use it
                logger.info(f"[CHAT:{request_id}] Attempting direct message processing")
                
                # Call the process_chat function
                from backend.api.chat import process_chat
                result = await process_chat(
                    message_text=chat_request.message,
                    thread_id=thread_id,
                    language=chat_request.language or "en"
                )
                
                process_duration = (datetime.now() - process_start).total_seconds()
                logger.info(f"[CHAT:{request_id}] process_chat completed in {process_duration:.3f}s")
                logger.debug(f"[CHAT:{request_id}] process_chat result: {result}")
                
                if not result.get("processed", False):
                    logger.error(f"[CHAT:{request_id}] Message processing failed: {result.get('error', 'Unknown error')}")
                    return {
                        "response": result.get("message", "I'm sorry, I encountered an error processing your request. Please try again."),
                        "thread_id": thread_id
                    }
                
                # If command was processed, include the command info
                if result.get("command_processed", False):
                    command_type = result.get("command_type", "unknown")
                    logger.info(f"[CHAT:{request_id}] Command processed successfully, type: {command_type}")
                    return {
                        "response": result.get("message", ""),
                        "thread_id": thread_id,
                        "command_processed": True,
                        "command_type": command_type,
                        "command_data": result.get("command_data", {})
                    }
                    
                return {
                    "response": result.get("message", ""),
                    "thread_id": thread_id
                }
            except ImportError as ie:
                logger.error(f"[CHAT:{request_id}] Import error during processing: {str(ie)}")
                logger.error(traceback.format_exc())
                
                # Fallback to direct workflow invocation
                logger.info(f"[CHAT:{request_id}] Falling back to direct workflow invocation")
                fallback_start = datetime.now()
                
                try:
                    # Create initial state
                    state = {
                        "messages": [],
                        "metadata": {
                            "thread_id": thread_id,
                            "language": chat_request.language or "en"
                        }
                    }
                    
                    # Get existing thread state
                    thread_state = await get_thread_state(thread_id)
                    if thread_state and not chat_request.reset_context:
                        logger.info(f"[CHAT:{request_id}] Retrieved existing thread state")
                        state = thread_state
                    
                    # Add the new message
                    state["messages"].append(HumanMessage(content=chat_request.message))
                    
                    # Get the workflow
                    workflow = await get_workflow()
                    
                    # Process the message
                    workflow_start = datetime.now()
                    logger.info(f"[CHAT:{request_id}] Invoking workflow directly")
                    state = await workflow.invoke(state)
                    workflow_duration = (datetime.now() - workflow_start).total_seconds()
                    logger.info(f"[CHAT:{request_id}] Direct workflow invocation completed in {workflow_duration:.3f}s")
                    
                    # Save the updated state
                    await save_thread_state(thread_id, state)
                    
                    # Extract response
                    messages = state.get("messages", [])
                    if messages and len(messages) > 0:
                        last_message = messages[-1]
                        response_text = getattr(last_message, "content", "") if hasattr(last_message, "content") else last_message.get("content", "")
                    else:
                        response_text = "I'm sorry, I couldn't generate a response."
                    
                    # Check if command was processed
                    command_processed = state.get("metadata", {}).get("command_processed", False)
                    command_type = state.get("metadata", {}).get("command_type", None)
                    command_data = state.get("metadata", {}).get("command_data", {})
                    
                    fallback_duration = (datetime.now() - fallback_start).total_seconds()
                    logger.info(f"[CHAT:{request_id}] Fallback processing completed in {fallback_duration:.3f}s")
                    
                    if command_processed:
                        logger.info(f"[CHAT:{request_id}] Command processed in fallback flow, type: {command_type}")
                        return {
                            "response": response_text,
                            "thread_id": thread_id,
                            "command_processed": True,
                            "command_type": command_type,
                            "command_data": command_data
                        }
                    else:
                        return {
                            "response": response_text,
                            "thread_id": thread_id
                        }
                except Exception as fallback_error:
                    logger.error(f"[CHAT:{request_id}] Fallback processing failed: {str(fallback_error)}")
                    logger.error(traceback.format_exc())
                    return {
                        "response": "I'm sorry, I encountered an unexpected error. Please try again later.",
                        "thread_id": thread_id
                    }
            except Exception as e:
                logger.error(f"[CHAT:{request_id}] Error in process_chat: {str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "response": "I'm sorry, I encountered an error processing your request. Please try again.",
                    "thread_id": thread_id
                }

        # Run the processing with a timeout
        try:
            logger.info(f"[CHAT:{request_id}] Starting processing with 25s timeout")
            timeout_start = datetime.now()
            result = await asyncio.wait_for(process_with_timeout(), timeout=25.0)
            timeout_duration = (datetime.now() - timeout_start).total_seconds()
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[CHAT:{request_id}] Request processed in {processing_time:.3f}s (timeout monitoring: {timeout_duration:.3f}s)")
            return result
        except asyncio.TimeoutError:
            timeout_duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"[CHAT:{request_id}] Request timed out after {timeout_duration:.3f} seconds")
            return {
                "response": "I'm sorry, but your request took too long to process. Please try a shorter or simpler message.",
                "thread_id": chat_request.thread_id or f"thread_{uuid.uuid4().hex[:12]}"
            }
    except Exception as e:
        error_time = (datetime.now() - start_time).total_seconds()
        logger.exception(f"[CHAT:{request_id}] Error processing chat request after {error_time:.3f}s: {e}")
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
    check_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()
    logger.info(f"[HEALTH:{check_id}] Health check endpoint called")
    
    try:
        # Now we can safely access the event loop inside an async function
        event_loop = asyncio.get_running_loop()
        logger.info(f"[HEALTH:{check_id}] Running in event loop: {event_loop}")
        
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
        redis_start = datetime.now()
        try:
            logger.info(f"[HEALTH:{check_id}] Testing Redis connection")
            # Use the new diagnostics function for detailed Redis information
            redis_diagnostics = await get_redis_diagnostics()
            redis_duration = (datetime.now() - redis_start).total_seconds()
            
            # Provide detailed Redis information
            results["services"]["redis"] = redis_diagnostics
            results["services"]["redis"]["check_duration_seconds"] = redis_duration
            logger.info(f"[HEALTH:{check_id}] Redis check completed in {redis_duration:.3f}s: {redis_diagnostics['status']}")
        except Exception as e:
            redis_duration = (datetime.now() - redis_start).total_seconds()
            logger.error(f"[HEALTH:{check_id}] Redis health check failed in {redis_duration:.3f}s: {e}")
            logger.exception(f"[HEALTH:{check_id}] Redis diagnostics error:")
            results["services"]["redis"] = {
                "status": "error", 
                "error": str(e),
                "check_duration_seconds": redis_duration,
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check thread state access
        state_start = datetime.now()
        try:
            logger.info(f"[HEALTH:{check_id}] Testing thread state access")
            test_thread_id = f"health-check-thread-{check_id}"
            test_data = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test write
            save_start = datetime.now()
            save_result = await save_thread_state(test_thread_id, test_data)
            save_duration = (datetime.now() - save_start).total_seconds()
            
            # Test read
            read_start = datetime.now()
            read_result = await get_thread_state(test_thread_id)
            read_duration = (datetime.now() - read_start).total_seconds()
            
            state_duration = (datetime.now() - state_start).total_seconds()
            
            results["services"]["thread_state"] = {
                "status": "working" if save_result and read_result and read_result.get("test") is True else "failing",
                "write_success": bool(save_result),
                "read_success": bool(read_result),
                "write_duration_seconds": save_duration,
                "read_duration_seconds": read_duration,
                "total_duration_seconds": state_duration
            }
            logger.info(f"[HEALTH:{check_id}] Thread state check completed in {state_duration:.3f}s: {results['services']['thread_state']['status']}")
        except Exception as e:
            state_duration = (datetime.now() - state_start).total_seconds()
            logger.error(f"[HEALTH:{check_id}] Thread state health check failed in {state_duration:.3f}s: {e}")
            results["services"]["thread_state"] = {
                "status": "error", 
                "error": str(e),
                "duration_seconds": state_duration,
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check if backend modules are available
        module_start = datetime.now()
        backend_available = False
        try:
            logger.info(f"[HEALTH:{check_id}] Checking backend module availability")
            import backend.workflow.workflow
            import backend.services.redis_service
            backend_available = True
            module_duration = (datetime.now() - module_start).total_seconds()
            results["backend_available"] = backend_available
            results["backend_modules_check_duration"] = module_duration
            logger.info(f"[HEALTH:{check_id}] Backend modules check completed in {module_duration:.3f}s: available")
        except Exception as e:
            module_duration = (datetime.now() - module_start).total_seconds()
            logger.error(f"[HEALTH:{check_id}] Backend modules not available (in {module_duration:.3f}s): {str(e)}")
            results["backend_available"] = False
            results["backend_error"] = str(e)
            results["backend_modules_check_duration"] = module_duration
        
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
        
        logger.info(f"[HEALTH:{check_id}] Health check completed in {process_time:.3f}s with status: {results['status']}")
        return JSONResponse(results)
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"[HEALTH:{check_id}] Health check failed in {process_time:.3f}s: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse({
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc().split("\n")[-10:],
            "duration_seconds": process_time
        }, status_code=500)

async def get_redis_diagnostics():
    """Get detailed Redis connection diagnostics"""
    diag_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()
    logger.info(f"[REDIS-DIAG:{diag_id}] Starting Redis diagnostics")
    
    results = {
        "status": "unknown",
        "version": None,
        "connection_test": False,
        "ping_latency_ms": None,
        "key_test": False
    }
    
    try:
        # Test basic connection
        conn_start = datetime.now()
        async with redis_connection() as client:
            conn_duration = (datetime.now() - conn_start).total_seconds()
            logger.info(f"[REDIS-DIAG:{diag_id}] Connection attempt took {conn_duration*1000:.1f}ms")
            
            if client is None:
                results["status"] = "disconnected"
                results["error"] = "Could not establish connection"
                results["connection_duration_ms"] = conn_duration * 1000
                logger.error(f"[REDIS-DIAG:{diag_id}] Redis connection failed: client is None")
                return results
                
            results["connection_test"] = True
            results["connection_duration_ms"] = conn_duration * 1000
            
            # Test ping
            ping_start = datetime.now()
            try:
                await client.ping()
                ping_duration = (datetime.now() - ping_start).total_seconds()
                results["ping_latency_ms"] = ping_duration * 1000
                logger.info(f"[REDIS-DIAG:{diag_id}] Ping successful in {ping_duration*1000:.1f}ms")
            except Exception as ping_error:
                logger.error(f"[REDIS-DIAG:{diag_id}] Ping failed: {str(ping_error)}")
                results["ping_error"] = str(ping_error)
            
            # Test basic key operations
            test_key = f"redis-diag-test-{diag_id}"
            key_start = datetime.now()
            try:
                # Set a test key
                await client.set(test_key, "test-value", ex=60)  # 60s expiration
                
                # Get the test key
                value = await client.get(test_key)
                
                # Delete the test key
                await client.delete(test_key)
                
                key_duration = (datetime.now() - key_start).total_seconds()
                results["key_test"] = (value == "test-value")
                results["key_operations_duration_ms"] = key_duration * 1000
                logger.info(f"[REDIS-DIAG:{diag_id}] Key operations {'successful' if results['key_test'] else 'failed'} in {key_duration*1000:.1f}ms")
            except Exception as key_error:
                logger.error(f"[REDIS-DIAG:{diag_id}] Key operations failed: {str(key_error)}")
                results["key_error"] = str(key_error)
            
            # Try to get server info
            try:
                info = await client.info()
                results["version"] = info.get("redis_version", "unknown")
                results["clients_connected"] = info.get("connected_clients", "unknown")
                results["memory_used"] = info.get("used_memory_human", "unknown")
                logger.info(f"[REDIS-DIAG:{diag_id}] Server info: Redis version {results['version']}, {results['clients_connected']} clients")
            except Exception as info_error:
                logger.error(f"[REDIS-DIAG:{diag_id}] Server info failed: {str(info_error)}")
                results["info_error"] = str(info_error)
    
    except Exception as e:
        logger.error(f"[REDIS-DIAG:{diag_id}] Redis diagnostics failed: {str(e)}")
        logger.error(traceback.format_exc())
        results["status"] = "error"
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc().split("\n")[-5:]
        return results
    
    # Determine overall status
    if results["connection_test"] and results["key_test"]:
        results["status"] = "healthy"
    elif results["connection_test"]:
        results["status"] = "degraded"
    else:
        results["status"] = "failing"
    
    total_duration = (datetime.now() - start_time).total_seconds()
    results["total_diagnostics_duration_ms"] = total_duration * 1000
    logger.info(f"[REDIS-DIAG:{diag_id}] Diagnostics completed in {total_duration*1000:.1f}ms with status: {results['status']}")
    
    return results

async def get_workflow():
    """Get or create the workflow for processing messages"""
    start_time = datetime.now()
    workflow_id = str(uuid.uuid4())[:8]
    logger.info(f"[WORKFLOW:{workflow_id}] Creating workflow for processing messages")
    
    try:
        from backend.workflow.workflow import create_workflow
        logger.info(f"[WORKFLOW:{workflow_id}] Successfully imported create_workflow function")
        
        try:
            # Need to await create_workflow since it's an async function
            logger.debug(f"[WORKFLOW:{workflow_id}] Calling create_workflow()")
            workflow_start = datetime.now()
            workflow = await create_workflow()
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            logger.info(f"[WORKFLOW:{workflow_id}] Successfully created workflow in {workflow_duration:.3f}s")
            
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[WORKFLOW:{workflow_id}] Total workflow creation time: {total_duration:.3f}s")
            return workflow
        except Exception as e:
            logger.error(f"[WORKFLOW:{workflow_id}] Error with imported create_workflow: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create a simple sequential workflow directly instead
            fallback_start = datetime.now()
            logger.info(f"[WORKFLOW:{workflow_id}] Attempting to create fallback workflow")
            
            from backend.workflow.workflow import WorkflowInvoker
            from backend.workflow.extract_context import extract_context
            from backend.workflow.select_domain import select_domain  
            from backend.workflow.generate_response import generate_response
            from backend.workflow.post_process import post_process
            
            logger.info(f"[WORKFLOW:{workflow_id}] Successfully imported workflow components")
            
            # Define a simple sequential workflow function that doesn't rely on async/await syntax
            async def simple_workflow_runner(state):
                try:
                    # Log the input state
                    msg_count = len(state.get('messages', []))
                    context_keys = list(state.get('context', {}).keys())
                    metadata_keys = list(state.get('metadata', {}).keys())
                    logger.info(f"[WORKFLOW-RUN:{workflow_id}] Processing workflow with {msg_count} messages, context keys: {context_keys}, metadata keys: {metadata_keys}")
                    
                    # Make a copy of the state to avoid modifying the original
                    current_state = state.copy()
                    
                    # Store original context to prevent accidental loss
                    import copy
                    original_context = copy.deepcopy(current_state.get("context", {}))
                    original_user_context = copy.deepcopy(current_state.get("user_context", {}))
                    
                    # Extract context
                    logger.info(f"[WORKFLOW-RUN:{workflow_id}] Running extract_context")
                    step_start = datetime.now()
                    try:
                        current_state = await extract_context(current_state)
                        step_duration = (datetime.now() - step_start).total_seconds()
                        logger.info(f"[WORKFLOW-RUN:{workflow_id}] extract_context completed in {step_duration:.3f}s")
                    except Exception as e:
                        logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error in extract_context: {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    # Select domain
                    logger.info(f"[WORKFLOW-RUN:{workflow_id}] Running select_domain")
                    step_start = datetime.now()
                    try:
                        current_state = await select_domain(current_state)
                        step_duration = (datetime.now() - step_start).total_seconds()
                        logger.info(f"[WORKFLOW-RUN:{workflow_id}] select_domain completed in {step_duration:.3f}s, selected domain: {current_state.get('domain', 'unknown')}")
                    except Exception as e:
                        logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error in select_domain: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Set a default domain if there's an error
                        current_state["domain"] = "general"
                        logger.info(f"[WORKFLOW-RUN:{workflow_id}] Fallback to default domain: general")
                    
                    # Generate response
                    logger.info(f"[WORKFLOW-RUN:{workflow_id}] Running generate_response")
                    step_start = datetime.now()
                    try:
                        current_state = await generate_response(current_state)
                        step_duration = (datetime.now() - step_start).total_seconds()
                        
                        # Count messages after generation
                        new_msg_count = len(current_state.get('messages', []))
                        logger.info(f"[WORKFLOW-RUN:{workflow_id}] generate_response completed in {step_duration:.3f}s, messages count: {new_msg_count}")
                    except Exception as e:
                        logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error in generate_response: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Add a fallback response if there's an error
                        try:
                            logger.info(f"[WORKFLOW-RUN:{workflow_id}] Adding fallback response message")
                            current_state["messages"].append(AIMessage(content="I apologize, but I encountered an error generating a response. Could you please try again?"))
                        except Exception as msg_error:
                            logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error adding message: {str(msg_error)}")
                            # Use a dict as fallback
                            current_state["messages"].append({"type": "ai", "content": "I apologize, but I encountered an error generating a response. Could you please try again?"})
                    
                    # Post-process
                    logger.info(f"[WORKFLOW-RUN:{workflow_id}] Running post_process")
                    step_start = datetime.now()
                    try:
                        current_state = await post_process(current_state)
                        step_duration = (datetime.now() - step_start).total_seconds()
                        
                        # Log command processing info if applicable
                        command_processed = current_state.get("metadata", {}).get("command_processed", False)
                        command_type = current_state.get("metadata", {}).get("command_type", "none")
                        logger.info(f"[WORKFLOW-RUN:{workflow_id}] post_process completed in {step_duration:.3f}s, command processed: {command_processed}, type: {command_type}")
                    except Exception as e:
                        logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error in post_process: {str(e)}")
                        logger.error(traceback.format_exc())
                    
                    # Check if context was lost during processing and restore it
                    if not current_state.get("context") and original_context:
                        logger.warning(f"[WORKFLOW-RUN:{workflow_id}] Context was lost during processing, restoring from backup")
                        current_state["context"] = original_context
                        
                    if not current_state.get("user_context") and original_user_context:
                        logger.warning(f"[WORKFLOW-RUN:{workflow_id}] User context was lost during processing, restoring from backup")
                        current_state["user_context"] = original_user_context
                    
                    total_duration = (datetime.now() - step_start).total_seconds()
                    logger.info(f"[WORKFLOW-RUN:{workflow_id}] Workflow execution completed successfully in {total_duration:.3f}s")
                    return current_state
                except Exception as e:
                    logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error in workflow execution: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Ensure we have a valid state to return
                    if "messages" not in state:
                        state["messages"] = []
                        
                    # Add a fallback error message
                    try:
                        state["messages"].append(AIMessage(content="I apologize, but I encountered an error processing your message. Please try again."))
                    except Exception as msg_error:
                        logger.error(f"[WORKFLOW-RUN:{workflow_id}] Error adding message: {str(msg_error)}")
                        # Use a dict as fallback
                        state["messages"].append({"type": "ai", "content": "I apologize, but I encountered an error processing your message. Please try again."})
                    
                    return state
            
            # Return a workflow invoker with our simple runner
            fallback_duration = (datetime.now() - fallback_start).total_seconds()
            logger.info(f"[WORKFLOW:{workflow_id}] Created fallback workflow in {fallback_duration:.3f}s")
            
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[WORKFLOW:{workflow_id}] Total workflow creation time (with fallback): {total_duration:.3f}s")
            return WorkflowInvoker(simple_workflow_runner)
            
        except Exception as e:
            logger.error(f"[WORKFLOW:{workflow_id}] Error creating direct workflow: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    except Exception as e:
        logger.error(f"[WORKFLOW:{workflow_id}] Error creating workflow: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Fallback to a simple workflow if the import fails
        try:
            logger.info(f"[WORKFLOW:{workflow_id}] Attempting to create emergency fallback workflow")
            emergency_start = datetime.now()
            
            from backend.workflow.workflow import WorkflowInvoker
            from backend.workflow.extract_context import extract_context
            from backend.workflow.select_domain import select_domain
            from backend.workflow.generate_response import generate_response
            from backend.workflow.post_process import post_process
            
            logger.info(f"[WORKFLOW:{workflow_id}] Creating fallback workflow")
            
            # Create a simple sequential workflow
            async def simple_workflow(state):
                try:
                    step_start = datetime.now()
                    logger.info(f"[WORKFLOW-EMERGENCY:{workflow_id}] Starting emergency workflow execution")
                    # Extract context
                    state = await extract_context(state)
                    
                    # Select domain
                    state = await select_domain(state)
                    
                    # Generate response
                    state = await generate_response(state)
                    
                    # Post-process
                    state = await post_process(state)
                    
                    step_duration = (datetime.now() - step_start).total_seconds()
                    logger.info(f"[WORKFLOW-EMERGENCY:{workflow_id}] Emergency workflow completed in {step_duration:.3f}s")
                    return state
                except Exception as workflow_error:
                    logger.error(f"[WORKFLOW-EMERGENCY:{workflow_id}] Error in simple workflow: {str(workflow_error)}")
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
            
            emergency_duration = (datetime.now() - emergency_start).total_seconds()
            logger.info(f"[WORKFLOW:{workflow_id}] Created emergency workflow in {emergency_duration:.3f}s")
            
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[WORKFLOW:{workflow_id}] Total workflow creation time (with emergency fallback): {total_duration:.3f}s")
            return WorkflowInvoker(simple_workflow)
        except Exception as fallback_error:
            logger.error(f"[WORKFLOW:{workflow_id}] Failed to create fallback workflow: {str(fallback_error)}")
            logger.error(traceback.format_exc())
            
            # Return an extremely simple workflow as last resort
            last_resort_start = datetime.now()
            logger.critical(f"[WORKFLOW:{workflow_id}] Creating LAST RESORT emergency workflow due to critical failures")
            
            class EmergencyWorkflow:
                async def invoke(self, state):
                    invoke_id = str(uuid.uuid4())[:8]
                    logger.error(f"[WORKFLOW-LAST-RESORT:{invoke_id}] Using EMERGENCY workflow due to critical errors in workflow creation")
                    
                    if "messages" not in state:
                        state["messages"] = []
                    
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
                        
                        logger.info(f"[WORKFLOW-LAST-RESORT:{invoke_id}] Emergency workflow returned response at {timestamp}")
                    except Exception as final_error:
                        logger.critical(f"[WORKFLOW-LAST-RESORT:{invoke_id}] Critical error in emergency response: {str(final_error)}")
                        # Last resort - use a dict
                        state["messages"].append({"type": "ai", "content": error_response})
                    
                    return state
            
            last_resort_duration = (datetime.now() - last_resort_start).total_seconds()
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.critical(f"[WORKFLOW:{workflow_id}] Created LAST RESORT emergency workflow in {last_resort_duration:.3f}s, total time: {total_duration:.3f}s")
            return EmergencyWorkflow()

@app.get("/api/warmup")
async def warmup():
    """
    Warmup endpoint to reduce cold start impact.
    This loads key components but doesn't execute expensive operations.
    """
    warmup_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()
    logger.info(f"[WARMUP:{warmup_id}] Warmup endpoint called")
    
    results = {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
        "duration_ms": 0
    }
    
    try:
        # Test Redis connection (lightweight operation)
        logger.info(f"[WARMUP:{warmup_id}] Testing Redis connection")
        redis_start = datetime.now()
        redis_available = await test_redis_connection()
        redis_duration = (datetime.now() - redis_start).total_seconds()
        
        results["components"]["redis"] = {
            "status": "available" if redis_available else "unavailable",
            "duration_ms": redis_duration * 1000
        }
        logger.info(f"[WARMUP:{warmup_id}] Redis test completed in {redis_duration:.3f}s: {'available' if redis_available else 'unavailable'}")
        
        # Pre-initialize workflow (but don't run it)
        logger.info(f"[WARMUP:{warmup_id}] Pre-initializing workflow")
        workflow_start = datetime.now()
        try:
            workflow = await get_workflow()
            workflow_type = type(workflow).__name__
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            
            results["components"]["workflow"] = {
                "status": "initialized",
                "type": workflow_type,
                "duration_ms": workflow_duration * 1000,
                "is_emergency": workflow_type == "EmergencyWorkflow"
            }
            logger.info(f"[WARMUP:{warmup_id}] Workflow initialization completed in {workflow_duration:.3f}s: {workflow_type}")
        except Exception as wf_error:
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            logger.error(f"[WARMUP:{warmup_id}] Workflow initialization failed in {workflow_duration:.3f}s: {str(wf_error)}")
            results["components"]["workflow"] = {
                "status": "failed",
                "error": str(wf_error),
                "duration_ms": workflow_duration * 1000
            }
        
        # Check if module imports are working
        logger.info(f"[WARMUP:{warmup_id}] Testing module imports")
        modules_start = datetime.now()
        modules_results = {}
        
        # Test key modules
        for module_name in ["fastapi", "redis", "langchain", "openai"]:
            try:
                module_import_start = datetime.now()
                if module_name == "fastapi":
                    import fastapi
                    modules_results[module_name] = {
                        "status": "available",
                        "version": fastapi.__version__
                    }
                elif module_name == "redis":
                    import redis
                    modules_results[module_name] = {
                        "status": "available",
                        "version": redis.__version__
                    }
                elif module_name == "langchain":
                    import langchain
                    modules_results[module_name] = {
                        "status": "available",
                        "version": getattr(langchain, "__version__", "unknown")
                    }
                elif module_name == "openai":
                    import openai
                    modules_results[module_name] = {
                        "status": "available",
                        "version": openai.__version__ if hasattr(openai, "__version__") else "unknown"
                    }
                
                module_import_duration = (datetime.now() - module_import_start).total_seconds()
                modules_results[module_name]["duration_ms"] = module_import_duration * 1000
                logger.info(f"[WARMUP:{warmup_id}] Module {module_name} import successful in {module_import_duration:.3f}s: version {modules_results[module_name]['version']}")
            except Exception as module_error:
                module_import_duration = (datetime.now() - module_import_start).total_seconds() if 'module_import_start' in locals() else 0
                modules_results[module_name] = {
                    "status": "failed",
                    "error": str(module_error),
                    "duration_ms": module_import_duration * 1000
                }
                logger.error(f"[WARMUP:{warmup_id}] Module {module_name} import failed in {module_import_duration:.3f}s: {str(module_error)}")
        
        modules_duration = (datetime.now() - modules_start).total_seconds()
        results["components"]["modules"] = modules_results
        results["components"]["modules"]["total_duration_ms"] = modules_duration * 1000
        logger.info(f"[WARMUP:{warmup_id}] Module imports testing completed in {modules_duration:.3f}s")
        
        # Return status
        total_duration = (datetime.now() - start_time).total_seconds()
        results["duration_ms"] = total_duration * 1000
        
        # Determine overall status
        component_statuses = [
            c.get("status") == "available" or c.get("status") == "initialized" 
            for c in [results["components"].get("redis", {}), results["components"].get("workflow", {})]
        ]
        
        if all(component_statuses):
            results["status"] = "ready"
        elif any(component_statuses):
            results["status"] = "degraded"
        else:
            results["status"] = "failed"
            
        logger.info(f"[WARMUP:{warmup_id}] Warmup completed in {total_duration:.3f}s with status: {results['status']}")
        return JSONResponse(results)
    except Exception as e:
        error_duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"[WARMUP:{warmup_id}] Error during warmup in {error_duration:.3f}s: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "duration_ms": error_duration * 1000
        }, status_code=500)

@app.get("/api/diagnostics")
async def diagnostics():
    """
    Diagnostic endpoint to help troubleshoot deployment issues.
    Returns detailed information about the running environment.
    """
    diag_id = str(uuid.uuid4())[:8]
    start_time = datetime.now()
    logger.info(f"[DIAG:{diag_id}] Diagnostics endpoint called")
    
    try:
        # Safely access event loop inside async function
        event_loop = asyncio.get_running_loop()
        logger.info(f"[DIAG:{diag_id}] Running in event loop: {event_loop}")
        
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
        logger.info(f"[DIAG:{diag_id}] Environment info collected")
        
        # Redis test with detailed information
        redis_start = datetime.now()
        logger.info(f"[DIAG:{diag_id}] Testing Redis connection")
        redis_info = await get_redis_diagnostics()
        redis_duration = (datetime.now() - redis_start).total_seconds()
        redis_info["diagnostics_duration_ms"] = redis_duration * 1000
        logger.info(f"[DIAG:{diag_id}] Redis diagnostics completed in {redis_duration:.3f}s: {redis_info.get('status', 'unknown')}")
        
        # Module availability
        modules_start = datetime.now()
        logger.info(f"[DIAG:{diag_id}] Collecting module information")
        modules_info = {}
        try:
            # FastAPI and web modules
            try:
                import fastapi
                modules_info["fastapi"] = {"version": fastapi.__version__, "location": fastapi.__file__}
                logger.debug(f"[DIAG:{diag_id}] FastAPI version: {fastapi.__version__}")
            except Exception as e:
                modules_info["fastapi"] = {"error": str(e)}
                logger.warning(f"[DIAG:{diag_id}] Error getting FastAPI info: {str(e)}")
                
            try:
                import pydantic
                modules_info["pydantic"] = {"version": pydantic.__version__, "location": pydantic.__file__}
                logger.debug(f"[DIAG:{diag_id}] Pydantic version: {pydantic.__version__}")
            except Exception as e:
                modules_info["pydantic"] = {"error": str(e)}
                logger.warning(f"[DIAG:{diag_id}] Error getting Pydantic info: {str(e)}")
                
            try:
                import starlette
                modules_info["starlette"] = {"version": starlette.__version__, "location": starlette.__file__}
                logger.debug(f"[DIAG:{diag_id}] Starlette version: {starlette.__version__}")
            except Exception as e:
                modules_info["starlette"] = {"error": str(e)}
                logger.warning(f"[DIAG:{diag_id}] Error getting Starlette info: {str(e)}")
            
            # Redis modules
            try:
                import redis
                modules_info["redis"] = {"version": redis.__version__, "location": redis.__file__}
                logger.debug(f"[DIAG:{diag_id}] Redis version: {redis.__version__}")
                
                try:
                    modules_info["redis.asyncio"] = {"available": hasattr(redis, "asyncio"), "location": redis.asyncio.__file__ if hasattr(redis, "asyncio") else None}
                    logger.debug(f"[DIAG:{diag_id}] Redis asyncio available: {hasattr(redis, 'asyncio')}")
                except Exception as e:
                    modules_info["redis.asyncio"] = {"error": str(e)}
                    logger.warning(f"[DIAG:{diag_id}] Error getting Redis asyncio info: {str(e)}")
            except Exception as e:
                modules_info["redis"] = {"error": str(e)}
                logger.warning(f"[DIAG:{diag_id}] Error getting Redis info: {str(e)}")
            
            # Check for key backend modules
            backend_modules = [
                ("backend.workflow.workflow", "workflow"),
                ("backend.services.redis_service", "redis_service"),
                ("backend.db.routine_db", "routine_db"),
                ("backend.api.chat", "chat"),
                ("backend.api.compatibility", "compatibility")
            ]
            
            for module_path, module_key in backend_modules:
                try:
                    module = __import__(module_path, fromlist=["*"])
                    modules_info[module_key] = {"available": True, "location": module.__file__}
                    logger.debug(f"[DIAG:{diag_id}] Module {module_path} available at {module.__file__}")
                except ImportError as ie:
                    modules_info[module_key] = {"available": False, "error": str(ie)}
                    logger.warning(f"[DIAG:{diag_id}] Module {module_path} not found: {str(ie)}")
                except Exception as e:
                    modules_info[module_key] = {"available": False, "error": str(e)}
                    logger.warning(f"[DIAG:{diag_id}] Error loading module {module_path}: {str(e)}")
                
        except Exception as e:
            modules_info["error"] = str(e)
            modules_info["traceback"] = traceback.format_exc().split("\n")
            logger.error(f"[DIAG:{diag_id}] Error collecting module information: {str(e)}")
            
        modules_duration = (datetime.now() - modules_start).total_seconds()
        modules_info["collection_duration_ms"] = modules_duration * 1000
        logger.info(f"[DIAG:{diag_id}] Module information collected in {modules_duration:.3f}s")
        
        # File system information
        fs_start = datetime.now()
        logger.info(f"[DIAG:{diag_id}] Collecting filesystem information")
        fs_info = {}
        try:
            # Check if we can write to the filesystem
            import tempfile
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp.write(b"test")
                fs_info["can_write_temp"] = True
                fs_info["temp_dir"] = tempfile.gettempdir()
                logger.debug(f"[DIAG:{diag_id}] Can write to temp directory: {tempfile.gettempdir()}")
        except Exception as e:
            fs_info["can_write_temp"] = False
            fs_info["temp_error"] = str(e)
            logger.warning(f"[DIAG:{diag_id}] Cannot write to temp directory: {str(e)}")
            
        try:
            # Check if we can read from the current directory
            current_dir = os.getcwd()
            files = os.listdir(current_dir)
            fs_info["current_dir"] = current_dir
            fs_info["dir_readable"] = True
            fs_info["file_count"] = len(files)
            fs_info["sample_files"] = files[:5]  # Just the first 5 files
            logger.debug(f"[DIAG:{diag_id}] Current directory {current_dir} contains {len(files)} files")
        except Exception as e:
            fs_info["dir_readable"] = False
            fs_info["dir_error"] = str(e)
            logger.warning(f"[DIAG:{diag_id}] Cannot read directory: {str(e)}")
            
        fs_duration = (datetime.now() - fs_start).total_seconds()
        fs_info["collection_duration_ms"] = fs_duration * 1000
        logger.info(f"[DIAG:{diag_id}] Filesystem information collected in {fs_duration:.3f}s")
        
        # Put everything together
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": env_info,
            "redis": redis_info,
            "modules": modules_info,
            "filesystem": fs_info
        }
        
        total_duration = (datetime.now() - start_time).total_seconds()
        result["total_diagnostics_duration_ms"] = total_duration * 1000
        logger.info(f"[DIAG:{diag_id}] Diagnostics completed in {total_duration:.3f}s")
        
        return JSONResponse(result)
    except Exception as e:
        error_duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"[DIAG:{diag_id}] Diagnostics endpoint error in {error_duration:.3f}s: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc().split("\n"),
            "duration_ms": error_duration * 1000
        }, status_code=500)
