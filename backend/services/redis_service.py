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

try:
    from backend.models.message_types import HumanMessage, AIMessage, BaseMessage
except ImportError:
    # For backward compatibility
    class BaseMessage:
        def to_dict(self): return {"content": str(self)}
    class HumanMessage(BaseMessage): pass
    class AIMessage(BaseMessage): pass

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
    return await execute_list_command(key, "rpush", value)

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

async def set_with_fallback(key: str, value: Any, expiry: int = None) -> bool:
    """Set a value in Redis with fallback to pickle file if Redis fails."""
    try:
        # Try Redis first
        client = await get_redis_client()
        if client:
            serialized = json.dumps(value)
            if expiry:
                await client.setex(key, expiry, serialized)
            else:
                await client.set(key, serialized)
            logger.info(f"Successfully set Redis key: {key}")
            return True
        else:
            # Redis is not available, use pickle fallback
            save_to_pickle(key, value)
            logger.info(f"Redis unavailable, saved key to pickle: {key}")
            return True
    except Exception as e:
        # Handle Redis errors with pickle fallback
        logger.warning(f"Error setting Redis key {key}: {e}. Using pickle fallback.")
        try:
            save_to_pickle(key, value)
            return True
        except Exception as e:
            logger.error(f"Fallback failed for key {key}: {e}")
            return False

async def delete_with_fallback(key: str) -> bool:
    """Delete a key from Redis with fallback to pickle file if Redis fails."""
    try:
        # Try Redis first
        client = await get_redis_client()
        if client:
            await client.delete(key)
            logger.info(f"Successfully deleted Redis key: {key}")
            return True
        else:
            # Redis is not available, use pickle fallback
            delete_from_pickle(key)
            logger.info(f"Redis unavailable, deleted key from pickle: {key}")
            return True
    except Exception as e:
        # Handle Redis errors with pickle fallback
        logger.warning(f"Error deleting Redis key {key}: {e}. Using pickle fallback.")
        try:
            delete_from_pickle(key)
            return True
        except Exception as e:
            logger.error(f"Fallback deletion failed for key {key}: {e}")
            return False

def save_to_pickle(key: str, value: Any) -> None:
    """Save value to a pickle file as fallback storage."""
    # Create directory if it doesn't exist
    os.makedirs("./data/cache", exist_ok=True)
    
    # Create a sanitized filename from the key
    # Replace characters that are invalid in filenames
    sanitized_key = key.replace(":", "_").replace("/", "_").replace("\\", "_")
    filepath = f"./data/cache/{sanitized_key}.pickle"
    
    with open(filepath, 'wb') as f:
        pickle.dump((value, int(time.time())), f)

def delete_from_pickle(key: str) -> None:
    """Delete a pickle file used as fallback storage."""
    # Create a sanitized filename from the key
    sanitized_key = key.replace(":", "_").replace("/", "_").replace("\\", "_")
    filepath = f"./data/cache/{sanitized_key}.pickle"
    
    # Check if file exists before attempting to delete
    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info(f"Deleted pickle file: {filepath}")
    else:
        logger.info(f"Pickle file not found: {filepath}") 