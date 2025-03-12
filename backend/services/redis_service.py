"""
Babywise Chatbot - Redis Service

This module provides Redis connection and operations for the Babywise Chatbot,
optimized for serverless environments.
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

# Per-request connection tracking (to avoid event loop conflicts)
_connection_cache = {}

async def get_redis() -> Optional[aioredis.Redis]:
    """
    Get a Redis connection appropriate for the current request.
    
    This function creates a fresh connection for each request context,
    which is safer in a serverless environment where event loops may differ.
    """
    try:
        # Get Redis URL from environment or use default
        redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
        if not redis_url:
            logger.error("Redis URL not configured")
            return None
            
        # Connect to Redis with modern from_url method
        client = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,  # Shorter timeout for serverless environment
            socket_connect_timeout=3.0,
            retry_on_timeout=True
        )
        
        try:
            # Validate connection
            await client.ping()
            return client
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            try:
                # Ensure proper cleanup of failed connection
                client.close()
                await client.wait_closed()
            except Exception:
                pass
            return None
            
    except Exception as e:
        logger.error(f"Error connecting to Redis: {e}")
        return None

async def initialize_redis() -> bool:
    """
    Test Redis connection and verify it works.
    
    For serverless environments, this does not maintain a connection pool
    but simply tests that we can connect.
    """
    try:
        # Test a connection
        client = await get_redis()
        if client is None:
            return False
            
        # Success - clean up immediately
        try:
            client.close()
            await client.wait_closed()
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
            
        return True
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        return False

async def test_redis_connection() -> bool:
    """Test the Redis connection."""
    try:
        client = await get_redis()
        if client is None:
            return False
            
        # Test connection
        await client.ping()
        
        # Clean up immediately
        try:
            client.close()
            await client.wait_closed()
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
            
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False

async def ensure_redis_initialized() -> bool:
    """Ensure Redis is initialized and working."""
    return await test_redis_connection()

# Helper function to get a value from Redis with memory fallback
async def get_with_fallback(key: str) -> Optional[Any]:
    """Get a value from Redis with fallback to memory cache."""
    # Try Redis first
    client = None
    try:
        client = await get_redis()
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
    finally:
        # Always clean up the connection
        if client:
            try:
                client.close()
                await client.wait_closed()
            except Exception:
                pass
    
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
    client = None
    try:
        client = await get_redis()
        if client:
            await client.set(key, value, ex=expiration)
            result = True
        else:
            result = False
    except Exception as e:
        logger.warning(f"Error setting {key} in Redis: {e}")
        result = False
    finally:
        # Always clean up the connection
        if client:
            try:
                client.close()
                await client.wait_closed()
            except Exception:
                pass
    
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
        return result  # Return Redis result if memory cache fails

async def delete_with_fallback(key: str) -> bool:
    """Delete a value from Redis with memory fallback cleanup."""
    client = None
    try:
        client = await get_redis()
        if client:
            await client.delete(key)
    except Exception as e:
        logger.warning(f"Error deleting {key} from Redis: {e}")
    finally:
        # Always clean up the connection
        if client:
            try:
                client.close()
                await client.wait_closed()
            except Exception:
                pass
    
    # Also clean from memory cache
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
    client = None
    try:
        client = await get_redis()
        if client is None:
            logger.error("Failed to get Redis connection for retrieving thread events")
            return []
            
        events = []
        # Get list of event keys for this thread
        thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
        event_keys = await client.lrange(thread_events_key, 0, -1)
        
        for event_key in event_keys:
            event_json = await client.get(event_key)
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
    finally:
        # Always clean up the connection
        if client:
            try:
                client.close()
                await client.wait_closed()
            except Exception:
                pass

# Helper function to execute a Redis list command with cleanup
async def execute_list_command(key: str, command: str, *args) -> bool:
    """Execute a Redis list command with proper connection cleanup."""
    client = None
    try:
        client = await get_redis()
        if client is None:
            return False
            
        # Execute the requested list command
        if command == 'rpush':
            await client.rpush(key, *args)
        elif command == 'lpush':
            await client.lpush(key, *args)
        else:
            logger.error(f"Unsupported list command: {command}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error executing {command} on {key}: {e}")
        return False
    finally:
        # Always clean up the connection
        if client:
            try:
                client.close()
                await client.wait_closed()
            except Exception:
                pass

# Add event to a thread's event list
async def add_event_to_thread(thread_id: str, event_key: str) -> bool:
    """Add an event key to a thread's event list."""
    thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
    return await execute_list_command(thread_events_key, 'rpush', event_key) 