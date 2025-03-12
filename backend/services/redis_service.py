"""
Babywise Chatbot - Redis Service

This module provides Redis connection and operations for the Babywise Chatbot,
optimized for serverless environments with complete connection isolation.
"""

import os
import json
import logging
import asyncio
import aioredis
import contextlib
from typing import Optional, Dict, Any, List, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
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

# Redis connection configuration
REDIS_URL = os.environ.get("STORAGE_URL", "redis://***:***@redis-10101.c135.eu-central-1-1.ec2.redns.redis-cloud.com:10101")

# In-memory fallback cache when Redis is unavailable - thread-safe with simpler structure
_memory_cache: Dict[str, Any] = {}

# Custom JSON encoder to handle message objects
class MessageJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can serialize message objects."""
    def default(self, obj):
        if isinstance(obj, (HumanMessage, AIMessage, BaseMessage)):
            return obj.to_dict()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

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
            socket_timeout=3.0,  # Even shorter timeout for serverless environment
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

async def initialize_redis() -> bool:
    """Initialize Redis (just a connection test for serverless environments)."""
    return await test_redis_connection()

async def ensure_redis_initialized() -> bool:
    """Ensure Redis is initialized (alias for test_redis_connection)."""
    return await test_redis_connection()

# Helper function to get a value from Redis with memory fallback
async def get_with_fallback(key: str) -> Optional[Any]:
    """Get a value from Redis with fallback to memory cache."""
    # Try Redis first
    try:
        async with redis_connection() as client:
            if client:
                value = await client.get(key)
                if value:
                    try:
                        result = json.loads(value)
                        return result
                    except json.JSONDecodeError:
                        return value
    except Exception as e:
        logger.warning(f"Error getting {key} from Redis: {e}")
    
    # Fall back to memory cache
    if key in _memory_cache:
        logger.info(f"Using memory cache fallback for {key}")
        return _memory_cache.get(key)
    
    return None

# Helper function to set a value in Redis with memory fallback
async def set_with_fallback(key: str, value: Any, expiration: int = THREAD_STATE_EXPIRATION) -> bool:
    """Set a value in Redis with fallback to memory cache."""
    # Convert value to JSON if it's not a string
    if not isinstance(value, str):
        try:
            value = json.dumps(value, cls=MessageJSONEncoder)
        except Exception as e:
            logger.error(f"Error serializing value for {key}: {e}")
            return False
    
    # Try Redis first
    redis_success = False
    try:
        async with redis_connection() as client:
            if client:
                await client.set(key, value, ex=expiration)
                redis_success = True
    except Exception as e:
        logger.warning(f"Error setting {key} in Redis: {e}")
    
    # Always update memory cache (regardless of Redis success)
    try:
        if isinstance(value, str):
            try:
                _memory_cache[key] = json.loads(value)
            except json.JSONDecodeError:
                _memory_cache[key] = value
        else:
            _memory_cache[key] = value
        logger.info(f"Stored {key} in memory cache fallback")
        return True
    except Exception as e:
        logger.error(f"Error setting {key} in memory cache: {e}")
        return redis_success  # Return Redis result if memory cache fails

async def delete_with_fallback(key: str) -> bool:
    """Delete a value from Redis with memory fallback cleanup."""
    redis_success = False
    try:
        async with redis_connection() as client:
            if client:
                await client.delete(key)
                redis_success = True
    except Exception as e:
        logger.warning(f"Error deleting {key} from Redis: {e}")
    
    # Always clean up memory cache
    if key in _memory_cache:
        del _memory_cache[key]
    
    return True

# Thread state functions
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the state for a thread."""
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    return await get_with_fallback(key)

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save the state for a thread."""
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    return await set_with_fallback(key, state, THREAD_STATE_EXPIRATION)

async def delete_thread_state(thread_id: str) -> bool:
    """Delete the state for a thread."""
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    return await delete_with_fallback(key)

# Routine summary cache functions
async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """Cache a routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, summary, SUMMARY_EXPIRATION)

async def get_cached_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get a cached routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

# Recent events functions
async def cache_recent_events(thread_id: str, routine_type: str, events: List[Dict[str, Any]]) -> bool:
    """Cache recent events."""
    key = f"{RedisKeyPrefix.RECENT_EVENTS}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, events, RECENT_EVENTS_EXPIRATION)

async def get_cached_recent_events(thread_id: str, routine_type: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached recent events."""
    key = f"{RedisKeyPrefix.RECENT_EVENTS}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

# Active routine functions
async def cache_active_routine(thread_id: str, routine_type: str, routine_data: Dict[str, Any]) -> bool:
    """Cache an active routine."""
    key = f"{RedisKeyPrefix.ACTIVE_ROUTINE}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, routine_data, ACTIVE_ROUTINE_EXPIRATION)

async def get_active_routine(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get a cached active routine."""
    key = f"{RedisKeyPrefix.ACTIVE_ROUTINE}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

async def invalidate_routine_cache(thread_id: str, routine_type: str) -> bool:
    """Invalidate routine caches for a thread and routine type."""
    try:
        # Delete all cache keys for this thread and routine type
        for prefix in [RedisKeyPrefix.ROUTINE_SUMMARY, RedisKeyPrefix.RECENT_EVENTS, RedisKeyPrefix.ACTIVE_ROUTINE]:
            key = f"{prefix}:{thread_id}:{routine_type}"
            await delete_with_fallback(key)
                
        logger.info(f"Invalidated routine cache for thread {thread_id}, type {routine_type}")
        return True
    except Exception as e:
        logger.error(f"Error invalidating routine cache: {e}")
        return False

async def get_thread_events(thread_id: str) -> List[Dict[str, Any]]:
    """Get all events for a thread."""
    events = []
    try:
        async with redis_connection() as client:
            if client is None:
                logger.error("Failed to get Redis connection for retrieving thread events")
                return []
                
            # Get list of event keys for this thread
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            event_keys = await client.lrange(thread_events_key, 0, -1)
            
            # Get event data
            for event_key in event_keys:
                event_json = await client.get(event_key)
                if event_json:
                    try:
                        event = json.loads(event_json)
                        events.append(event)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse event JSON for key {event_key}")
    except Exception as e:
        logger.error(f"Error getting thread events: {e}")
    
    return events

# Add event to a thread's event list
async def add_event_to_thread(thread_id: str, event_key: str) -> bool:
    """Add an event key to a thread's event list."""
    thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
    try:
        async with redis_connection() as client:
            if client is None:
                return False
            
            await client.rpush(thread_events_key, event_key)
            return True
    except Exception as e:
        logger.error(f"Error adding event to thread list: {e}")
        return False

# Direct Redis list operation with proper cleanup
async def list_append(key: str, value: str) -> bool:
    """Append a value to a Redis list with proper connection handling."""
    try:
        async with redis_connection() as client:
            if client is None:
                return False
            
            await client.rpush(key, value)
            return True
    except Exception as e:
        logger.error(f"Error appending to list {key}: {e}")
        return False

# Get multiple values from Redis in a single connection
async def multi_get(keys: List[str]) -> Dict[str, Any]:
    """Get multiple values from Redis in a single connection."""
    result = {}
    try:
        async with redis_connection() as client:
            if client is None:
                return {}
            
            # Use Redis Pipeline for efficiency
            pipe = client.pipeline()
            for key in keys:
                pipe.get(key)
            
            values = await pipe.execute()
            
            # Process results
            for i, key in enumerate(keys):
                if values[i] is not None:
                    try:
                        result[key] = json.loads(values[i])
                    except json.JSONDecodeError:
                        result[key] = values[i]
    except Exception as e:
        logger.error(f"Error in multi_get: {e}")
    
    return result 