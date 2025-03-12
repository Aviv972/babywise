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
from backend.models.message_types import HumanMessage, AIMessage, BaseMessage

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Redis connection configuration
REDIS_URL = "redis://***:***@redis-10101.c135.eu-central-1-1.ec2.redns.redis-cloud.com:10101"
_redis_pool = None
_event_loop = None

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

def get_event_loop():
    """Get or create an event loop for Redis operations."""
    global _event_loop
    try:
        _event_loop = asyncio.get_running_loop()
    except RuntimeError:
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
    return _event_loop

async def initialize_redis() -> None:
    """Initialize the Redis connection pool with proper error handling."""
    global _redis_pool
    try:
        if _redis_pool is None:
            logger.info("Initializing Redis connection pool...")
            _redis_pool = await aioredis.create_redis_pool(
                REDIS_URL,
                minsize=1,
                maxsize=10,
                encoding='utf-8',
                decode_responses=True
            )
            logger.info("Redis connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis connection pool: {e}")
        raise

async def get_redis() -> Optional[aioredis.Redis]:
    """Get a Redis connection from the pool with proper error handling."""
    try:
        if _redis_pool is None:
            await initialize_redis()
        if _redis_pool is not None:
            try:
                await _redis_pool.ping()
            except Exception:
                logger.warning("Redis connection lost, reinitializing...")
                await close_redis()
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

# Redis client instance
_redis_client = None

# Cache key prefixes
ROUTINE_SUMMARY_PREFIX = "routine_summary:"
RECENT_EVENTS_PREFIX = "recent_events:"
ACTIVE_ROUTINE_PREFIX = "active_routine:"
THREAD_STATE_PREFIX = "thread_state:"

# Cache expiration times (in seconds)
SUMMARY_EXPIRATION = 3600  # 1 hour
RECENT_EVENTS_EXPIRATION = 1800  # 30 minutes
ACTIVE_ROUTINE_EXPIRATION = 7200  # 2 hours
THREAD_STATE_EXPIRATION = 86400  # 24 hours

# Connection timeout in seconds - increased for Vercel environment
REDIS_CONNECTION_TIMEOUT = 10.0

# In-memory fallback cache when Redis is unavailable
_memory_cache: Dict[str, Dict[str, Any]] = {}

class RedisKeyPrefix(str, Enum):
    """Redis key prefixes for different types of data."""
    THREAD_STATE = "thread_state"
    EVENT = "event"
    THREAD_EVENTS = "thread_events"
    ROUTINE_SUMMARY = "routine_summary"
    RECENT_EVENTS = "recent_events"
    ACTIVE_ROUTINE = "active_routine"

class CacheEntry:
    """Class to represent a cached entry with metadata."""
    def __init__(self, value: Any, expiration: int):
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=expiration)
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def access(self) -> None:
        self.access_count += 1
        self.last_accessed = datetime.now()

class RedisManager:
    """Class to manage Redis connection and operations."""
    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._last_connection_attempt = datetime.min
        self._connection_backoff = 1  # Initial backoff in seconds
        self._max_backoff = 30  # Maximum backoff in seconds
        self._connection_lock = asyncio.Lock()
        self._event_loop = None

    def _get_event_loop(self):
        """Get or create an event loop for Redis operations."""
        if self._event_loop is None:
            try:
                self._event_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Get Redis client with improved connection management."""
        if self._client is not None:
            try:
                await self._client.ping()
                return self._client
            except Exception as e:
                logger.warning(f"Redis connection test failed: {e}")
                self._client = None

        async with self._connection_lock:
            now = datetime.now()
            if (now - self._last_connection_attempt).total_seconds() < self._connection_backoff:
                return None

            try:
                redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
                if not redis_url:
                    logger.error("Redis URL not configured")
                    return None

                masked_url = redis_url.replace(redis_url.split('@')[0] if '@' in redis_url else redis_url, '***:***@')
                logger.info(f"Attempting Redis connection to {masked_url}")

                loop = self._get_event_loop()
                self._client = await aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=10.0,
                    socket_connect_timeout=5.0,
                    retry_on_timeout=True
                )

                await self._client.ping()
                self._connection_backoff = 1
                logger.info("Redis connection established successfully")
                return self._client

            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self._client = None
                self._last_connection_attempt = now
                self._connection_backoff = min(self._connection_backoff * 2, self._max_backoff)
                return None

    async def close(self):
        """Close Redis connection safely."""
        if self._client is not None:
            try:
                self._client.close()
                await self._client.wait_closed()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._client = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with fallback to memory cache."""
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                entry.access()
                return entry.value
            else:
                del self._memory_cache[key]

        # Try Redis
        client = await self.get_client()
        if client:
            try:
                value = await client.get(key)
                if value:
                    parsed = json.loads(value)
                    # Update memory cache
                    self._memory_cache[key] = CacheEntry(parsed, 3600)
                    return parsed
            except Exception as e:
                logger.error(f"Redis get operation failed for key {key}: {e}")

        return None

    async def set(self, key: str, value: Any, expiration: int = 3600) -> bool:
        """Set value in Redis with fallback to memory cache."""
        # Always update memory cache
        self._memory_cache[key] = CacheEntry(value, expiration)

        # Try Redis
        client = await self.get_client()
        if client:
            try:
                # Use custom encoder for serialization
                json_value = json.dumps(value, cls=MessageJSONEncoder)
                await client.set(key, json_value, ex=expiration)
                return True
            except Exception as e:
                logger.error(f"Redis set operation failed for key {key}: {e}")

        return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis and memory cache."""
        # Always remove from memory cache
        self._memory_cache.pop(key, None)

        # Try Redis
        client = await self.get_client()
        if client:
            try:
                await client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete operation failed for key {key}: {e}")

        return False

# Global Redis manager instance
_redis_manager = RedisManager()

# Expose high-level functions
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get thread state with robust error handling."""
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    try:
        return await _redis_manager.get(key)
    except Exception as e:
        logger.error(f"Error getting thread state for {thread_id}: {e}")
        return None

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save thread state with robust error handling."""
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    try:
        return await _redis_manager.set(key, state, 86400)  # 24 hours
    except Exception as e:
        logger.error(f"Error saving thread state for {thread_id}: {e}")
        return False

async def delete_thread_state(thread_id: str) -> bool:
    """Delete thread state with robust error handling."""
    key = f"{RedisKeyPrefix.THREAD_STATE}:{thread_id}"
    try:
        return await _redis_manager.delete(key)
    except Exception as e:
        logger.error(f"Error deleting thread state for {thread_id}: {e}")
        return False

# Routine-specific cache operations
async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """Cache a routine summary"""
    key = f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}"
    return await _redis_manager.set(key, summary, SUMMARY_EXPIRATION)

async def get_cached_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get a cached routine summary"""
    key = f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}"
    return await _redis_manager.get(key)

async def cache_recent_events(thread_id: str, routine_type: str, events: List[Dict[str, Any]]) -> bool:
    """Cache recent routine events"""
    key = f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}"
    return await _redis_manager.set(key, events, RECENT_EVENTS_EXPIRATION)

async def get_cached_recent_events(thread_id: str, routine_type: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached recent events"""
    key = f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}"
    return await _redis_manager.get(key)

async def cache_active_routine(thread_id: str, routine_type: str, routine_data: Dict[str, Any]) -> bool:
    """Cache an active routine"""
    key = f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
    return await _redis_manager.set(key, routine_data, ACTIVE_ROUTINE_EXPIRATION)

async def get_active_routine(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get an active routine"""
    key = f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
    return await _redis_manager.get(key)

async def invalidate_routine_cache(thread_id: str, routine_type: str) -> bool:
    """Invalidate all cached data for a routine type"""
    try:
        keys = [
            f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}",
            f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}",
            f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
        ]
        
        for key in keys:
            await _redis_manager.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error invalidating routine cache: {str(e)}")
        return False

async def get_thread_events(thread_id: str) -> List[Dict[str, Any]]:
    """Get all events for a thread from Redis."""
    try:
        redis = await get_redis()
        key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
        
        event_keys = await redis.lrange(key, 0, -1)
        events = []
        
        for event_key in event_keys:
            event_json = await redis.get(event_key)
            if event_json:
                events.append(json.loads(event_json))
        
        return events
        
    except Exception as e:
        logger.error(f"Error getting thread events: {e}")
        raise 