"""
Babywise Chatbot - Redis Service

This module provides Redis connection and operations for the Babywise Chatbot.
"""

import os
import json
import logging
import asyncio
import aioredis
from typing import Optional, Dict, Any, List, Tuple
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
_redis_pool = None

# In-memory fallback cache when Redis is unavailable
_memory_cache = {}

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

async def initialize_redis() -> None:
    """Initialize the Redis connection pool with proper error handling."""
    global _redis_pool
    try:
        if _redis_pool is None:
            logger.info("Initializing Redis connection pool...")
            
            # Get Redis URL from environment or use default
            redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
            if not redis_url:
                logger.error("Redis URL not configured")
                return
                
            # Create a masked URL for logging (hide credentials)
            masked_url = redis_url.replace(redis_url.split('@')[0] if '@' in redis_url else redis_url, '***:***@')
            logger.info(f"Connecting to Redis at {masked_url}")
            
            # Connect to Redis with modern from_url method (no loop parameter)
            _redis_pool = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=10.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True
            )
            
            logger.info("Redis connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis connection pool: {e}")
        _redis_pool = None

async def get_redis() -> Optional[aioredis.Redis]:
    """Get a Redis connection from the pool with proper error handling."""
    global _redis_pool
    try:
        if _redis_pool is None:
            await initialize_redis()
        
        if _redis_pool is not None:
            try:
                # Test the connection
                await _redis_pool.ping()
                return _redis_pool
            except Exception as e:
                logger.warning(f"Redis connection lost, reinitializing: {e}")
                _redis_pool = None
                await initialize_redis()
                
        return _redis_pool
    except Exception as e:
        logger.error(f"Error getting Redis connection: {e}")
        return None

async def close_redis() -> None:
    """Close the Redis connection pool safely."""
    global _redis_pool
    if _redis_pool is not None:
        try:
            logger.info("Closing Redis connection pool...")
            _redis_pool.close()
            await _redis_pool.wait_closed()
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {e}")
        finally:
            _redis_pool = None
            logger.info("Redis connection pool closed")

async def test_redis_connection() -> bool:
    """Test the Redis connection."""
    try:
        redis = await get_redis()
        if redis is None:
            return False
        await redis.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False

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

# Helper function to get a key with memory cache fallback
async def get_with_fallback(key: str) -> Optional[Any]:
    """Get a value from Redis with fallback to memory cache."""
    # Try Redis first
    redis = await get_redis()
    if redis:
        try:
            value = await redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        except Exception as e:
            logger.warning(f"Error getting {key} from Redis: {e}")
    
    # Fall back to memory cache
    if key in _memory_cache:
        logger.info(f"Using memory cache fallback for {key}")
        return _memory_cache.get(key)
    
    return None

# Helper function to set a key with memory cache fallback
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
    redis = await get_redis()
    if redis:
        try:
            await redis.set(key, value, ex=expiration)
            return True
        except Exception as e:
            logger.warning(f"Error setting {key} in Redis: {e}")
    
    # Fall back to memory cache
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
        return False

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
    redis = await get_redis()
    if redis:
        try:
            await redis.delete(key)
        except Exception as e:
            logger.warning(f"Error deleting {key} from Redis: {e}")
    
    if key in _memory_cache:
        del _memory_cache[key]
    
    return True

# Routine summary cache functions
async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """Cache a routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, summary, SUMMARY_EXPIRATION)

async def get_cached_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get a cached routine summary."""
    key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

async def cache_recent_events(thread_id: str, routine_type: str, events: List[Dict[str, Any]]) -> bool:
    """Cache recent events."""
    key = f"{RedisKeyPrefix.RECENT_EVENTS}:{thread_id}:{routine_type}"
    return await set_with_fallback(key, events, RECENT_EVENTS_EXPIRATION)

async def get_cached_recent_events(thread_id: str, routine_type: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached recent events."""
    key = f"{RedisKeyPrefix.RECENT_EVENTS}:{thread_id}:{routine_type}"
    return await get_with_fallback(key)

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
        redis = await get_redis()
        if redis is None:
            # Just clear memory cache
            for prefix in [RedisKeyPrefix.ROUTINE_SUMMARY, RedisKeyPrefix.RECENT_EVENTS, RedisKeyPrefix.ACTIVE_ROUTINE]:
                key = f"{prefix}:{thread_id}:{routine_type}"
                if key in _memory_cache:
                    del _memory_cache[key]
            return True
            
        # Delete all cache keys for this thread and routine type
        for prefix in [RedisKeyPrefix.ROUTINE_SUMMARY, RedisKeyPrefix.RECENT_EVENTS, RedisKeyPrefix.ACTIVE_ROUTINE]:
            key = f"{prefix}:{thread_id}:{routine_type}"
            await redis.delete(key)
            
            # Also clear from memory cache
            if key in _memory_cache:
                del _memory_cache[key]
                
        logger.info(f"Invalidated routine cache for thread {thread_id}, type {routine_type}")
        return True
    except Exception as e:
        logger.error(f"Error invalidating routine cache: {e}")
        return False

async def get_thread_events(thread_id: str) -> List[Dict[str, Any]]:
    """Get all events for a thread."""
    try:
        redis = await get_redis()
        if redis is None:
            return []
            
        events = []
        # Get list of event keys for this thread
        thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
        event_keys = await redis.lrange(thread_events_key, 0, -1)
        
        for event_key in event_keys:
            event_json = await redis.get(event_key)
            if event_json:
                try:
                    event = json.loads(event_json)
                    events.append(event)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse event JSON for key {event_key}")
        
        return events
    except Exception as e:
        logger.error(f"Error getting thread events: {e}")
        return [] 