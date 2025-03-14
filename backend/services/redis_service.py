"""
Babywise Assistant - Redis Service

This module provides Redis operations for the Babywise Assistant,
using redis.asyncio for modern Python compatibility.
"""

import os
import json
import logging
import asyncio
import contextlib
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
from backend.services.redis_compat import get_redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Export the functions needed by other modules
__all__ = [
    'redis_connection', 
    'get_thread_state',
    'save_thread_state', 
    'delete_thread_state',
    'add_event_to_thread',
    'list_append',
    'RedisKeyPrefix',
    'get_with_fallback',
    'set_with_fallback',
    'delete_with_fallback',
    'cache_routine_summary',
    'get_cached_routine_summary',
    'cache_recent_events',
    'get_cached_recent_events',
    'cache_active_routine',
    'get_active_routine',
    'invalidate_routine_cache',
    'get_thread_events',
    'get_redis',
    'initialize_redis',
    'ensure_redis_initialized'
]

# In-memory fallback cache
_memory_cache: Dict[str, Any] = {}

# Define Redis key prefixes as Enum for backward compatibility
class RedisKeyPrefix(str, Enum):
    """Redis key prefixes for different types of data."""
    THREAD_STATE = "thread_state"
    EVENT = "event"
    THREAD_EVENTS = "thread_events"
    ROUTINE_SUMMARY = "routine_summary"
    RECENT_EVENTS = "recent_events"
    ACTIVE_ROUTINE = "active_routine"

# Define key prefixes for Redis
THREAD_STATE_PREFIX = "thread_state"
EVENT_PREFIX = "event"
THREAD_EVENTS_PREFIX = "thread_events"
ROUTINE_SUMMARY_PREFIX = "routine_summary"
RECENT_EVENTS_PREFIX = "recent_events"

# Expiration times (in seconds)
THREAD_STATE_EXPIRATION = 86400  # 24 hours
ROUTINE_SUMMARY_EXPIRATION = 3600  # 1 hour
RECENT_EVENTS_EXPIRATION = 1800  # 30 minutes
ACTIVE_ROUTINE_EXPIRATION = 7200  # 2 hours

@contextlib.asynccontextmanager
async def redis_connection() -> AsyncGenerator[Optional[Any], None]:
    """
    Context manager for Redis connections to ensure proper cleanup.
    This function is maintained for backward compatibility.
    """
    client = None
    try:
        client = await get_redis_client()
        yield client
    finally:
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get thread state from Redis with memory fallback."""
    if not thread_id:
        logger.warning("get_thread_state called with empty thread_id")
        return None
        
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    
    try:
        client = await get_redis_client()
        if client:
            value = await client.get(key)
            await client.close()
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON for {key}")
                    return None
        
        # Memory fallback
        if key in _memory_cache:
            logger.info(f"Using memory cache for key {key}")
            return _memory_cache[key]
    except Exception as e:
        logger.error(f"Error getting thread state: {e}")
    
    return None

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save thread state to Redis with memory fallback."""
    if not thread_id:
        logger.warning("save_thread_state called with empty thread_id")
        return False
        
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    
    try:
        # Serialize state - handle non-serializable objects with default=str
        value = json.dumps(state, default=str)
        
        # Try Redis first
        client = await get_redis_client()
        if client:
            await client.set(key, value, ex=THREAD_STATE_EXPIRATION)
            await client.close()
            logger.info(f"Saved thread state to Redis for {thread_id}")
        
        # Always update memory cache
        _memory_cache[key] = state
        logger.info(f"Saved thread state to memory cache for {thread_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving thread state: {e}")
        return False

async def delete_thread_state(thread_id: str) -> bool:
    """Delete thread state from Redis and memory cache."""
    if not thread_id:
        logger.warning("delete_thread_state called with empty thread_id")
        return False
        
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    
    try:
        # Try Redis first
        client = await get_redis_client()
        if client:
            await client.delete(key)
            await client.close()
            logger.info(f"Deleted thread state from Redis for {thread_id}")
        
        # Always clean memory cache
        if key in _memory_cache:
            del _memory_cache[key]
            logger.info(f"Deleted thread state from memory cache for {thread_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting thread state: {e}")
        return False

# Add required functions needed by routine_db.py
async def add_event_to_thread(thread_id: str, event_key: str) -> bool:
    """Add an event key to a thread's events list."""
    if not thread_id or not event_key:
        logger.warning("add_event_to_thread called with empty parameters")
        return False
        
    key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
    
    try:
        client = await get_redis_client()
        if client:
            await client.rpush(key, event_key)
            await client.close()
            logger.info(f"Added event {event_key} to thread {thread_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding event to thread: {e}")
        return False

async def list_append(key: str, value: str) -> bool:
    """Append a value to a Redis list."""
    try:
        client = await get_redis_client()
        if client:
            await client.rpush(key, value)
            await client.close()
            logger.info(f"Appended value to list {key}")
        return True
    except Exception as e:
        logger.error(f"Error appending to list: {e}")
        return False

# Backward compatibility functions
async def get_with_fallback(key: str, default=None):
    """Get a value from Redis with fallback to memory cache."""
    try:
        client = await get_redis_client()
        if client:
            value = await client.get(key)
            await client.close()
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        
        # Memory fallback
        if key in _memory_cache:
            logger.info(f"Using memory cache for key {key}")
            return _memory_cache[key]
    except Exception as e:
        logger.error(f"Error getting value: {e}")
    
    return default

async def set_with_fallback(key: str, value: Any, expiry: int = None) -> bool:
    """Set a value in Redis with fallback to memory cache."""
    try:
        # Serialize value
        serialized = json.dumps(value, default=str)
        
        # Try Redis first
        client = await get_redis_client()
        if client:
            if expiry:
                await client.setex(key, expiry, serialized)
            else:
                await client.set(key, serialized)
            await client.close()
            logger.info(f"Set value in Redis for key {key}")
        
        # Always update memory cache
        _memory_cache[key] = value
        logger.info(f"Set value in memory cache for key {key}")
        return True
    except Exception as e:
        logger.error(f"Error setting value: {e}")
        return False

async def delete_with_fallback(key: str) -> bool:
    """Delete a value from Redis with fallback to memory cache."""
    try:
        # Try Redis first
        client = await get_redis_client()
        if client:
            await client.delete(key)
            await client.close()
            logger.info(f"Deleted value from Redis for key {key}")
        
        # Always clean memory cache
        if key in _memory_cache:
            del _memory_cache[key]
            logger.info(f"Deleted value from memory cache for key {key}")
        return True
    except Exception as e:
        logger.error(f"Error deleting value: {e}")
        return False

# Add the missing routine summary functions
async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """Cache a routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, summary, ROUTINE_SUMMARY_EXPIRATION)

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
        client = await get_redis_client()
        if client:
            # Get all event keys for this thread
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            event_keys = await client.lrange(thread_events_key, 0, -1)
            await client.close()
            events = event_keys or []
    except Exception as e:
        logger.error(f"Error retrieving thread events for {thread_id}: {e}")
    
    return events

# Add functions for routine events if needed
# ... 

# Add get_redis function referenced in routine_tracker.py
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

# We maintain the function signature but delegate to compatibility layer
async def initialize_redis() -> bool:
    """Initialize Redis (just a connection test for serverless environments)."""
    client = await get_redis_client()
    if client:
        await client.close()
        return True
    return False

async def ensure_redis_initialized() -> bool:
    """Ensure Redis is initialized (alias for initialize_redis)."""
    return await initialize_redis() 