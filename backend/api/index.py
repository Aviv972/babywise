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

# Import aioredis patch before any other imports
try:
    logger.info("Importing aioredis_patch module...")
    from backend.api.aioredis_patch import patch_result as aioredis_patch_result
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
import aioredis

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
async def redis_connection() -> AsyncGenerator[Optional[aioredis.Redis], None]:
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
            client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
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
                        client.close()
                        await client.wait_closed()
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
                client.close()
                await client.wait_closed()
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
            
            # Initialize state with thread context from request
            state = {
                "messages": [],
                "metadata": {
                    "thread_id": thread_id,
                    "timestamp": datetime.now().isoformat(),
                    "timezone": chat_request.timezone or "UTC",
                    "request_id": request_id,
                    "language": chat_request.language or "en"
                },
                "context": chat_request.context or {},
                "user_context": chat_request.user_context or {},
                "language": chat_request.language or "en"
            }
            
            # Add the new message to the state
            if chat_request.message:
                try:
                    state["messages"].append(HumanMessage(content=chat_request.message))
                    logger.info(f"Added human message to state: {chat_request.message[:50]}...")
                except Exception as msg_error:
                    logger.error(f"Error adding message to state: {str(msg_error)}")
                    # Create a simple dict as fallback
                    state["messages"].append({"type": "human", "content": chat_request.message})
            
            # Get previous messages for this thread if any
            try:
                logger.info(f"Getting thread state for {thread_id}")
                thread_state = await get_thread_state(thread_id)
                if thread_state:
                    logger.info(f"Found existing thread state for {thread_id}")
                    # Merge previous messages with new message
                    previous_messages = thread_state.get("messages", [])
                    
                    if previous_messages:
                        logger.info(f"Found {len(previous_messages)} previous messages")
                        
                        # Convert message dicts to Message objects if needed
                        previous_message_objects = []
                        for msg in previous_messages:
                            try:
                                if isinstance(msg, dict):
                                    if msg.get("type") == "human":
                                        previous_message_objects.append(HumanMessage(content=msg.get("content", "")))
                                    else:
                                        previous_message_objects.append(AIMessage(content=msg.get("content", "")))
                                else:
                                    previous_message_objects.append(msg)
                            except Exception as msg_convert_error:
                                logger.warning(f"Error converting message: {str(msg_convert_error)}")
                                # Skip problematic messages
                                continue
                        
                        # Keep only the last 10 messages to prevent token limits
                        state["messages"] = previous_message_objects[-10:] + state["messages"]
                        logger.info(f"Added {len(previous_message_objects)} previous messages to state")
                    
                    # Merge context if it exists
                    if thread_state.get("context") and (not chat_request.context or not chat_request.reset_context):
                        # Only update context if it exists in thread_state and we're not resetting
                        state["context"] = thread_state.get("context", {})
                        logger.info(f"Loaded context from thread state, size: {len(json.dumps(state['context'], default=str))} bytes")
                    
                    # Merge user context if it exists
                    if thread_state.get("user_context") and not chat_request.reset_context:
                        state["user_context"] = thread_state.get("user_context", {})
                        logger.info(f"Loaded user context from thread state")
            except Exception as e:
                logger.error(f"Error loading thread state: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue with empty/new state if thread state loading fails
            
            # Ensure minimum context structure exists
            if not state.get("context"):
                logger.info("Initializing empty context with default structure")
                state["context"] = {
                    "thread_id": thread_id,
                    "user_timezone": chat_request.timezone or "UTC",
                    "last_updated": datetime.utcnow().isoformat(),
                    "baby_info": {},
                    "routines": {
                        "sleep": [],
                        "feeding": []
                    }
                }
            
            # Process the message through the workflow
            try:
                logger.info("Getting workflow")
                workflow = get_workflow()
                logger.info(f"Invoking workflow with state containing {len(state.get('messages', []))} messages")
                updated_state = await workflow.invoke(state)
                logger.info("Workflow processing completed successfully")
            except Exception as workflow_error:
                logger.error(f"Error in workflow processing: {str(workflow_error)}")
                logger.error(traceback.format_exc())
                
                # Create a minimal response with error message
                error_message = "I apologize, but I encountered an error while processing your message. Please try again."
                
                # Try to use the original state or create a new one
                if not state.get("messages"):
                    state["messages"] = []
                    
                # Add the error message
                try:
                    state["messages"].append(AIMessage(content=error_message))
                except Exception:
                    state["messages"].append({"type": "ai", "content": error_message})
                
                updated_state = state
            
            # Save updated state to Redis
            # First make sure any new information in the original context is preserved
            # if there was a temporary context used for this request
            try:
                if chat_request.context and not chat_request.reset_context:
                    updated_context = updated_state.get("context", {})
                    for key, value in chat_request.context.items():
                        if key not in updated_context:
                            updated_context[key] = value
                    updated_state["context"] = updated_context
                
                # Preserve important fields
                if "metadata" not in updated_state:
                    updated_state["metadata"] = {}
                updated_state["metadata"]["thread_id"] = thread_id
                
                # Extract the response message
                response_message = None
                for message in reversed(updated_state.get("messages", [])):
                    try:
                        # Check if it's a message object with a 'type' attribute
                        if hasattr(message, 'type'):
                            if message.type != "human":
                                response_message = message.content
                                break
                        # Check if it's a message with a dictionary type
                        elif isinstance(message, dict) and message.get("type") != "human":
                            response_message = message.get("content", "")
                            break
                        # Check if it's an AI message 
                        elif isinstance(message, AIMessage):
                            response_message = message.content
                            break
                    except Exception as msg_error:
                        logger.warning(f"Error processing message: {str(msg_error)}")
                        continue
                
                # If no response message was found, add a default one
                if not response_message:
                    error_message = "I apologize, but I couldn't generate a proper response. Please try again."
                    try:
                        updated_state["messages"].append(AIMessage(content=error_message))
                    except Exception:
                        updated_state["messages"].append({"type": "ai", "content": error_message})
                    response_message = error_message
                
                # Save the state to Redis
                logger.info(f"Saving context to Redis for thread {thread_id}")
                try:
                    # Use default=str to handle non-serializable objects
                    if updated_state.get('context'):
                        # Take a subset of keys for logging
                        context_subset = {k: v for k, v in updated_state.get('context', {}).items() if k in ['baby_info', 'routines']}
                        context_sample = json.dumps(context_subset, default=str)
                    else:
                        context_sample = "{}"
                        
                    if updated_state.get('user_context'):
                        # Take only first few items from user context
                        user_context_keys = list(updated_state.get('user_context', {}).keys())[:5]
                        user_context_subset = {k: updated_state['user_context'][k] for k in user_context_keys if k in updated_state.get('user_context', {})}
                        user_context_sample = json.dumps(user_context_subset, default=str)
                    else:
                        user_context_sample = "{}"
                        
                    logger.info(f"Context sample: {context_sample[:100]}...")
                    logger.info(f"User context sample: {user_context_sample[:100]}...")
                except Exception as json_error:
                    logger.warning(f"Error logging context: {str(json_error)}")
                    logger.warning(traceback.format_exc())
                
                success = await save_thread_state(thread_id, updated_state)
                if success:
                    logger.info(f"Saved thread state to Redis for {thread_id}")
                else:
                    logger.warning(f"Failed to save thread state to Redis for {thread_id}")
            except Exception as state_error:
                logger.error(f"Error saving state: {str(state_error)}")
                logger.error(traceback.format_exc())
            
            # Prepare command data if command was processed
            command_processed = updated_state.get("metadata", {}).get("command_processed", False)
            command_type = updated_state.get("metadata", {}).get("command_type")
            command_data = updated_state.get("metadata", {}).get("command_data", {})
            
            # Build the response
            return {
                "response": response_message or "I apologize, but I couldn't generate a response at this time.",
                "thread_id": thread_id,
                "command_processed": command_processed,
                "command_type": command_type,
                "command_data": command_data
            }
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(process_with_timeout(), timeout=25.0)
            
            # Calculate and log execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Request {request_id} processed in {execution_time:.2f} seconds")
            
            return result
        except asyncio.TimeoutError:
            logger.error(f"Request {request_id} timed out after 25 seconds")
            return {
                "response": "I'm sorry, but it's taking me longer than expected to process your message. Please try again with a simpler request.",
                "thread_id": chat_request.thread_id or f"thread_{uuid.uuid4().hex[:12]}",
                "command_processed": False,
                "command_type": None,
                "command_data": None
            }
    except Exception as e:
        # Log the error
        logger.error(f"Unhandled error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Calculate execution time for this failed request
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Request {request_id} failed after {execution_time:.2f} seconds")
        
        # Return a graceful error response
        return {
            "response": "I apologize, but I encountered an unexpected error while processing your message. Our team has been notified of the issue. Please try again later.",
            "thread_id": chat_request.thread_id or f"thread_{uuid.uuid4().hex[:12]}",
            "command_processed": False,
            "command_type": None,
            "command_data": None
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
            from backend.services.redis_compat import get_redis_diagnostics
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
            import aioredis
            modules_info["aioredis"] = {"version": getattr(aioredis, "__version__", "unknown"), "location": aioredis.__file__}
            
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

def get_workflow():
    """Get or create the workflow for processing messages"""
    try:
        from backend.workflow.workflow import create_workflow
        logger.info("Creating workflow using imported create_workflow function")
        return create_workflow()
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
                    
                    state["messages"].append(AIMessage(content="I apologize, but I encountered an error while processing your message. Please try again."))
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
                    
                    # Try multiple imports to ensure we can create a message
                    try:
                        from backend.models.message_types import AIMessage
                    except ImportError:
                        try:
                            from langchain_core.messages import AIMessage
                        except ImportError:
                            # Define a simple message class as last resort
                            class AIMessage:
                                def __init__(self, content):
                                    self.content = content
                                    self.type = "ai"
                    
                    state["messages"].append(AIMessage(content="I'm sorry, but I'm having trouble processing messages right now. Our team is working on a fix."))
                    return state
            
            return EmergencyWorkflow()
