"""
Babywise Chatbot - Redis Service

This module provides Redis connection and operations for the Babywise Chatbot,
optimized for serverless environments with complete connection isolation.
"""

import os
import json
import logging
import asyncio
import contextlib
from typing import Optional, Dict, Any, List, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
import pickle
import time

# Import from compatibility layer instead of directly importing aioredis
from backend.services.redis_compat import (
    redis_connection,
    test_redis_connection,
    get_with_fallback,
    set_with_fallback,
    delete_with_fallback,
    MessageJSONEncoder
)

# Define exports explicitly to avoid import issues
__all__ = [
    'redis_connection', 'RedisKeyPrefix', 'get_with_fallback', 'set_with_fallback',
    'delete_with_fallback', 'add_event_to_thread', 'list_append', 'get_thread_state',
    'save_thread_state', 'get_redis_client'
]

try:
    from backend.models.message_types import HumanMessage, AIMessage, BaseMessage
except ImportError:
    # For backward compatibility
    class BaseMessage:
        def to_dict(self): return {"content": str(self)}
    class HumanMessage(BaseMessage): pass
    class AIMessage(BaseMessage): pass

# Update to use LangChain message types
try:
    # First try to import from langchain_core (preferred)
    from langchain_core.messages import HumanMessage, AIMessage
except ImportError:
    try:
        # Fall back to traditional models if needed
        from backend.models.message_types import HumanMessage, AIMessage, BaseMessage
    except ImportError:
        # Provide minimal implementation for backward compatibility
        class BaseMessage:
            def __init__(self, content=""):
                self.content = content
            def to_dict(self): 
                return {"content": str(self.content)}
        class HumanMessage(BaseMessage): 
            @property
            def type(self): return "human"
        class AIMessage(BaseMessage):
            @property
            def type(self): return "ai"

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Redis connection configuration - kept for backward compatibility
REDIS_URL = os.environ.get("STORAGE_URL", "redis://***:***@redis-10101.c135.eu-central-1-1.ec2.redns.redis-cloud.com:10101")

# In-memory fallback cache is now handled in the compatibility layer
_memory_cache: Dict[str, Any] = {}

# Cache key prefixes
class RedisKeyPrefix(str, Enum):
    """Redis key prefixes for different types of data."""
    THREAD_STATE = "thread_state"
    EVENT = "event"
    THREAD_EVENTS = "thread_events"
    ROUTINE_SUMMARY = "routine_summary"
    RECENT_EVENTS = "recent_events"
    ACTIVE_ROUTINE = "active_routine"

# Cache expiration times (in seconds)
SUMMARY_EXPIRATION = 3600  # 1 hour
RECENT_EVENTS_EXPIRATION = 1800  # 30 minutes
ACTIVE_ROUTINE_EXPIRATION = 7200  # 2 hours
THREAD_STATE_EXPIRATION = 86400  # 24 hours

# We maintain the function signature but delegate to compatibility layer
async def initialize_redis() -> bool:
    """Initialize Redis (just a connection test for serverless environments)."""
    return await test_redis_connection()

async def ensure_redis_initialized() -> bool:
    """Ensure Redis is initialized (alias for test_redis_connection)."""
    return await test_redis_connection()

# Thread state functions
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the state for a thread."""
    if not thread_id:
        logger.warning("get_thread_state called with empty thread_id")
        return None
    
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    return await get_with_fallback(key)

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save the state for a thread."""
    if not thread_id:
        logger.warning("save_thread_state called with empty thread_id")
        return False
    
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    return await set_with_fallback(key, state, THREAD_STATE_EXPIRATION)

async def delete_thread_state(thread_id: str) -> bool:
    """Delete the state for a thread."""
    if not thread_id:
        logger.warning("delete_thread_state called with empty thread_id")
        return False
    
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    return await delete_with_fallback(key)

# Routine summary caching
async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """Cache a routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, summary, SUMMARY_EXPIRATION)

async def get_cached_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get a cached routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

# Recent events caching
async def cache_recent_events(thread_id: str, routine_type: str, events: List[Dict[str, Any]]) -> bool:
    """Cache recent events."""
    key = f"{RedisKeyPrefix.RECENT_EVENTS}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, events, RECENT_EVENTS_EXPIRATION)

async def get_cached_recent_events(thread_id: str, routine_type: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached recent events."""
    key = f"{RedisKeyPrefix.RECENT_EVENTS}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

# Active routine caching
async def cache_active_routine(thread_id: str, routine_type: str, active: bool) -> bool:
    """Cache active routine status."""
    key = f"{RedisKeyPrefix.ACTIVE_ROUTINE}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, {"active": active}, ACTIVE_ROUTINE_EXPIRATION)

async def get_active_routine(thread_id: str, routine_type: str) -> bool:
    """Get active routine status."""
    key = f"{RedisKeyPrefix.ACTIVE_ROUTINE}:{thread_id}:{routine_type}"
    result = await get_with_fallback(key)
    return result.get("active", False) if result else False

# Cache invalidation
async def invalidate_routine_cache(thread_id: str) -> bool:
    """Invalidate all routine cache entries for a thread."""
    success = True
    # Delete all related cache entries
    for prefix in [RedisKeyPrefix.ROUTINE_SUMMARY, RedisKeyPrefix.RECENT_EVENTS, RedisKeyPrefix.ACTIVE_ROUTINE]:
        sleep_key = f"{prefix}:{thread_id}:sleep"
        feeding_key = f"{prefix}:{thread_id}:feeding"
        
        if not await delete_with_fallback(sleep_key):
            success = False
        if not await delete_with_fallback(feeding_key):
            success = False
    
    return success

# Thread events list operations
async def get_thread_events(thread_id: str) -> List[str]:
    """Get all event keys for a thread."""
    events = []
    
    try:
        async with redis_connection() as client:
            if not client:
                logger.error("Failed to get Redis connection for retrieving thread events")
                return []
            
            # Get all event keys for this thread
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            event_keys = await client.lrange(thread_events_key, 0, -1)
            events = event_keys or []
    except Exception as e:
        logger.error(f"Error retrieving thread events for {thread_id}: {e}")
    
    return events

async def add_event_to_thread(thread_id: str, event_key: str) -> bool:
    """Add an event key to a thread's events list."""
    success = False
    
    try:
        thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
        async with redis_connection() as client:
            if not client:
                logger.error("Failed to get Redis connection for adding event to thread")
                return False
            
            # Add event key to thread events list
            await client.rpush(thread_events_key, event_key)
            success = True
    except Exception as e:
        logger.error(f"Error adding event {event_key} to thread {thread_id}: {e}")
    
    return success

# Direct Redis list operation with proper cleanup
async def execute_list_command(key: str, command: str, value: str) -> bool:
    """Append a value to a Redis list with proper connection handling."""
    try:
        async with redis_connection() as client:
            if not client:
                return False
            
            if command == "rpush":
                await client.rpush(key, value)
            elif command == "lpush":
                await client.lpush(key, value)
            else:
                logger.error(f"Unsupported list command: {command}")
                return False
                
            return True
    except Exception as e:
        logger.error(f"Error executing list command {command} for {key}: {e}")
        return False

# Add list_append function that was referenced in routine_db.py but was missing
async def list_append(key: str, value: str) -> bool:
    """
    Append a value to a Redis list.
    This is a convenience wrapper around execute_list_command using rpush.
    """
    logger.debug(f"Appending to list {key}: {value}")
    try:
        async with redis_connection() as client:
            if not client:
                logger.error(f"Failed to get Redis connection for list operation on {key}")
                return False
            
            # Add value to the list
            await client.rpush(key, value)
            logger.info(f"Successfully appended to list {key}")
            return True
    except Exception as e:
        logger.error(f"Error appending to list {key}: {e}")
        return False

# Add get_redis function referenced in routine_tracker.py but was missing
async def get_redis():
    """
    Get a Redis connection.
    This is a convenience function that returns the redis_connection context manager.
    
    Usage:
        async with get_redis() as client:
            # Use Redis client
            await client.get("my_key")
    """
    logger.debug("Creating Redis connection via get_redis()")
    return redis_connection()

# Get multiple values from Redis in a single connection
async def get_multiple(keys: List[str]) -> Dict[str, Any]:
    """Get multiple values from Redis in a single connection."""
    result = {}
    
    try:
        async with redis_connection() as client:
            if not client:
                return {}
            
            # Use Redis Pipeline for efficiency
            pipeline = client.pipeline()
            for key in keys:
                pipeline.get(key)
            
            values = await pipeline.execute()
            
            # Process results
            for i, key in enumerate(keys):
                if values[i]:
                    try:
                        result[key] = json.loads(values[i])
                    except json.JSONDecodeError:
                        result[key] = values[i]
    except Exception as e:
        logger.error(f"Error getting multiple keys {keys}: {e}")
    
    return result

# Add the missing get_redis_client function which should have been implemented
async def get_redis_client():
    """
    Get a Redis client instance.
    This wraps the redis_connection context manager to provide a client instance.
    """
    try:
        # Use the existing redis_connection context manager
        client = await redis_connection().__aenter__()
        if not client:
            logger.warning("Failed to get Redis client, returning None")
            return None
        return client
    except Exception as e:
        logger.error(f"Error getting Redis client: {e}")
        return None

async def set_with_fallback(key: str, value: Any, expiry: int = None) -> bool:
    """Set a value in Redis with fallback to in-memory cache for serverless environments."""
    try:
        # Try Redis first
        client = await get_redis_client()
        if client:
            serialized = json.dumps(value, cls=MessageJSONEncoder)
            if expiry:
                await client.setex(key, expiry, serialized)
            else:
                await client.set(key, serialized)
            logger.info(f"Successfully set Redis key: {key}")
            return True
        else:
            # Redis is not available, use in-memory fallback
            _memory_cache[key] = {
                "value": value,
                "timestamp": datetime.now().timestamp(),
                "expiry": expiry
            }
            logger.info(f"Redis unavailable, stored key in memory: {key}")
            return True
    except Exception as e:
        # Handle Redis errors with memory fallback
        logger.warning(f"Error setting Redis key {key}: {e}. Using memory fallback.")
        try:
            _memory_cache[key] = {
                "value": value,
                "timestamp": datetime.now().timestamp(),
                "expiry": expiry
            }
            logger.info(f"Stored key in memory fallback: {key}")
            return True
        except Exception as e:
            logger.error(f"All fallbacks failed for key {key}: {e}")
            return False

async def delete_with_fallback(key: str) -> bool:
    """Delete a key from Redis with fallback to in-memory cache for serverless environments."""
    try:
        # Try Redis first
        client = await get_redis_client()
        if client:
            await client.delete(key)
            logger.info(f"Successfully deleted Redis key: {key}")
            
            # Also clear from memory cache in case it exists there
            if key in _memory_cache:
                del _memory_cache[key]
            
            return True
        else:
            # Redis is not available, use in-memory fallback
            if key in _memory_cache:
                del _memory_cache[key]
                logger.info(f"Redis unavailable, deleted key from memory: {key}")
            return True
    except Exception as e:
        # Handle Redis errors with memory fallback
        logger.warning(f"Error deleting Redis key {key}: {e}. Trying memory fallback.")
        try:
            if key in _memory_cache:
                del _memory_cache[key]
                logger.info(f"Deleted key from memory fallback: {key}")
            return True
        except Exception as e:
            logger.error(f"All fallbacks failed for deleting key {key}: {e}")
            return False

# Replace the filesystem-based fallback functions with in-memory versions
# since Vercel has a read-only filesystem

async def get_with_fallback(key: str) -> Any:
    """Get a value from Redis with fallback to in-memory cache for serverless environments."""
    try:
        # Try Redis first
        async with redis_connection() as client:
            if client:
                value = await client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            
            # If Redis fails or key doesn't exist, check memory cache
            if key in _memory_cache:
                cached_item = _memory_cache[key]
                now = datetime.now().timestamp()
                
                # Check if expired
                if cached_item["expiry"] and (now - cached_item["timestamp"]) > cached_item["expiry"]:
                    del _memory_cache[key]
                    logger.info(f"Memory cache item expired for key: {key}")
                    return None
                
                logger.info(f"Retrieved key from memory cache: {key}")
                return cached_item["value"]
            
            return None
    except Exception as e:
        logger.warning(f"Error getting Redis key {key}: {e}. Checking memory fallback.")
        
        # Try memory cache
        if key in _memory_cache:
            cached_item = _memory_cache[key]
            now = datetime.now().timestamp()
            
            # Check if expired
            if cached_item["expiry"] and (now - cached_item["timestamp"]) > cached_item["expiry"]:
                del _memory_cache[key]
                logger.info(f"Memory cache item expired for key: {key}")
                return None
            
            logger.info(f"Retrieved key from memory cache: {key}")
            return cached_item["value"]
        
        return None 