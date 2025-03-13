"""
Babywise Chatbot - Redis Compatibility Layer

This module provides a compatibility layer between aioredis and redis.asyncio,
allowing for a smooth transition while maintaining the same API.
"""

import os
import json
import logging
import asyncio
import contextlib
import sys
import traceback
from typing import Optional, Dict, Any, List, AsyncGenerator, Union
from datetime import datetime

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Redis connection configuration
REDIS_URL = os.environ.get("STORAGE_URL", "redis://localhost:6379/0")

# In-memory fallback cache when Redis is unavailable
_memory_cache: Dict[str, Any] = {}

# Define exception classes that will be used regardless of which backend is imported
class RedisError(Exception): pass
class ConnectionError(RedisError): pass
class TimeoutError(RedisError): pass
class AuthenticationError(ConnectionError): pass
class ResponseError(RedisError): pass
class DataError(RedisError): pass

# Create a basic MockRedis class with the minimum implementation needed
class MockRedis:
    """
    Mock Redis implementation for when Redis is unavailable.
    
    This class simulates a Redis client with the minimum functionality needed
    to support the application. It stores data in memory and provides both
    sync and async methods to match the interfaces of both redis.asyncio and aioredis.
    """
    
    def __init__(self, *args, **kwargs):
        self._data = {}
        logger.warning("Created MockRedis instance - Redis functionality will be limited to in-memory operations")
    
    # Core Redis operations (async)
    async def ping(self):
        """Simulates Redis PING command. Always returns 'PONG'."""
        logger.info("MockRedis: PING called")
        return "PONG"
    
    async def get(self, key):
        """Simulates Redis GET command. Returns value from in-memory store."""
        logger.info(f"MockRedis: GET {key}")
        return self._data.get(key)
    
    async def set(self, key, value, ex=None):
        """Simulates Redis SET command. Stores value in memory."""
        logger.info(f"MockRedis: SET {key} (expiry: {ex})")
        self._data[key] = value
        return True
    
    async def delete(self, key):
        """Simulates Redis DELETE command. Removes value from memory."""
        logger.info(f"MockRedis: DELETE {key}")
        if key in self._data:
            del self._data[key]
            return 1
        return 0
    
    async def info(self):
        """Simulates Redis INFO command. Returns mock server information."""
        logger.info("MockRedis: INFO called")
        return {
            "redis_version": "mock",
            "redis_mode": "standalone",
            "used_memory_human": "0K",
            "connected_clients": "1",
            "uptime_seconds": "0"
        }
    
    # Connection management methods
    # We need both sync and async versions, but Python doesn't allow method overloading by return type
    # Instead, we'll use a different name for the async version and provide the sync version normally
    
    # For redis.asyncio compatibility - async close method
    async def close(self):
        """Async close method for redis.asyncio compatibility."""
        logger.info("MockRedis: async close() called")
        # No actual cleanup needed for mock
        return True
    
    # For aioredis compatibility - sync close method implemented on the class directly  
    # This is handled by a descriptor class to avoid method conflicts
    
    # For aioredis compatibility
    async def wait_closed(self):
        """Async wait_closed method for aioredis compatibility."""
        logger.info("MockRedis: wait_closed() called")
        # No actual waiting needed for mock
        return True
    
    # Extra methods that might be called by different Redis clients
    def __del__(self):
        """Destructor method to handle cleanup if object is garbage collected."""
        logger.info("MockRedis: __del__ called")
        # No cleanup needed

# Add a descriptor to handle the sync close method without conflicting with the async one
class SyncMethodDescriptor:
    """
    A descriptor class to add a synchronous method to a class
    that already has an async method with the same name.
    """
    def __init__(self, name, func):
        self.name = name
        self.func = func
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.func.__get__(obj, objtype)

# Define the sync close function
def sync_close(self):
    """Sync close method for aioredis compatibility."""
    logger.info("MockRedis: sync close() called via descriptor")
    # No actual cleanup needed for mock
    return True

# Add the sync close method to MockRedis
MockRedis.close = SyncMethodDescriptor('close', sync_close)

# Determine which Redis client to use
USE_REDIS_ASYNCIO = os.environ.get("USE_REDIS_ASYNCIO", "True").lower() in ("true", "1", "yes")

# Define a helper class for when Redis imports fail
class RedisImportFallback:
    """Fallback class when Redis imports fail. Contains stub methods for Redis functionality."""
    
    class Redis:
        """Mock Redis class that will give clear error messages when used."""
        
        @staticmethod
        async def from_url(*args, **kwargs):
            """Creates a MockRedis instance instead of a real Redis client."""
            logger.error("Using fallback Redis.from_url - real Redis not imported successfully")
            return MockRedis()
        
        @classmethod
        async def create_client(cls, *args, **kwargs):
            """Creates a MockRedis instance as a fallback."""
            logger.error("Using fallback Redis.create_client - real Redis not imported successfully")
            return MockRedis()
    
    @staticmethod
    async def from_url(*args, **kwargs):
        """Legacy aioredis-style from_url that returns a MockRedis."""
        logger.error("Using fallback from_url - real Redis not imported successfully")
        return MockRedis()

# Import the appropriate Redis client
redis = None
redis_backend = "none"
import_error = None

# First, ensure we always have a fallback as a last resort
# This guarantees redis is always defined
redis = RedisImportFallback()
redis_backend = "fallback_initial"

try:
    if USE_REDIS_ASYNCIO:
        # Try modern approach with redis.asyncio
        try:
            import redis as redis_pkg
            from redis import asyncio as redis_client
            from redis.exceptions import (
                AuthenticationError as RedisAuthError, 
                ConnectionError as RedisConnError,
                TimeoutError as RedisTimeoutError,
                ResponseError as RedisResponseError,
                DataError as RedisDataError
            )
            redis = redis_client
            redis_backend = "redis.asyncio"
            logger.info("Successfully imported redis.asyncio for Redis operations")
        except ImportError as e:
            import_error = f"Failed to import redis.asyncio: {e}"
            logger.warning(import_error)
            # Keep using the fallback that's already set
    
    # If redis.asyncio import failed or we're configured to use aioredis, try aioredis
    if redis_backend == "fallback_initial":
        try:
            import aioredis as redis_client
            from aioredis.exceptions import (
                AuthenticationError as RedisAuthError, 
                ConnectionError as RedisConnError,
                TimeoutError as RedisTimeoutError,
                ResponseError as RedisResponseError,
                DataError as RedisDataError
            )
            redis = redis_client
            redis_backend = "aioredis"
            logger.info("Successfully imported aioredis for Redis operations")
        except ImportError as e:
            import_error = f"Failed to import aioredis: {e}"
            logger.warning(import_error)
            # Keep using the fallback that's already set
    
    # No need to set fallback again - it's already set by default
except Exception as e:
    import_error = f"Unexpected error during Redis imports: {e}"
    logger.error(import_error)
    logger.error(traceback.format_exc())
    # Keep using the fallback that's already set

# Log the final state of the Redis client
logger.info(f"Final Redis backend: {redis_backend}")
if redis_backend.startswith("fallback"):
    logger.warning("Using fallback Redis implementation - limited functionality")

# Get Redis connection details for logging
redis_url_masked = REDIS_URL
if "://" in redis_url_masked:
    parts = redis_url_masked.split("://", 1)
    if "@" in parts[1]:
        # Mask credentials in URL for security in logs
        auth_server = parts[1].split("@", 1)
        redis_url_masked = f"{parts[0]}://***:***@{auth_server[1]}"

logger.info(f"Redis backend: {redis_backend}, URL: {redis_url_masked}")

# Custom JSON encoder to handle message objects
class MessageJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can serialize message objects and datetime objects."""
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Enhanced Redis retry mechanism
async def with_retries(func, *args, max_retries=3, backoff_factor=0.5, **kwargs):
    """
    Execute a Redis function with automatic retries and exponential backoff.
    
    Args:
        func: The async function to execute
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor to calculate wait time between retries
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        The result of the function call
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            wait_time = backoff_factor * (2 ** attempt)
            logger.warning(f"Redis operation failed (attempt {attempt+1}/{max_retries}), retrying in {wait_time:.2f}s: {str(e)}")
            last_error = e
            await asyncio.sleep(wait_time)
    
    # If we get here, all retries failed
    logger.error(f"Redis operation failed after {max_retries} attempts: {str(last_error)}")
    raise last_error

@contextlib.asynccontextmanager
async def redis_connection() -> AsyncGenerator[Optional[Any], None]:
    """
    Context manager for Redis connections to ensure proper cleanup.
    
    This creates a completely isolated connection for a single operation
    and guarantees it will be properly closed regardless of success or failure.
    
    Usage:
        async with redis_connection() as client:
            if client:
                # Use redis connection here
                await client.get("my_key")
    """
    client = None
    
    try:
        # Try to establish a connection with retries
        for attempt in range(3):
            try:
                # Use the imported redis module instead of undefined Redis
                client = await redis.from_url(
                    REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                
                # Test the connection
                await client.ping()
                
                yield client
                break
            except (ConnectionError, TimeoutError) as e:
                wait_time = 0.5 * (2 ** attempt)
                if attempt < 2:  # Don't log for the last attempt
                    logger.warning(f"Redis connection failed (attempt {attempt+1}/3), retrying in {wait_time:.2f}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Redis connection failed after 3 attempts: {str(e)}")
                    yield None
    except Exception as e:
        logger.error(f"Error establishing Redis connection: {str(e)}")
        yield None
    finally:
        # Ensure proper cleanup
        if client:
            try:
                await client.close()
                client = None
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {str(e)}")

async def test_redis_connection() -> bool:
    """Test Redis connection with retries."""
    try:
        async with redis_connection() as client:
            if client:
                await client.ping()
                return True
            return False
    except Exception as e:
        logger.error(f"Redis connection test failed: {str(e)}")
        return False

# Helper functions that maintain the same API regardless of underlying implementation

async def get_with_fallback(key, default=None):
    """Get a value from Redis with fallback to memory cache."""
    try:
        async with redis_connection() as client:
            if client:
                try:
                    # Try to get the value with retries
                    value = await with_retries(client.get, key)
                    if value:
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return value
                except Exception as e:
                    logger.error(f"Error getting key {key} from Redis: {str(e)}")
        
        # If Redis fails, check memory cache
        if key in _memory_cache:
            logger.info(f"Using memory cache for key {key}")
            return _memory_cache[key]
            
    except Exception as e:
        logger.error(f"Error in get_with_fallback for key {key}: {str(e)}")
    
    return default

async def set_with_fallback(key, value, expiry=None):
    """Set a value in Redis with fallback to memory cache."""
    success = False
    
    try:
        async with redis_connection() as client:
            if client:
                try:
                    # Try to set the value with retries
                    serialized = json.dumps(value, cls=MessageJSONEncoder)
                    if expiry:
                        await with_retries(client.setex, key, expiry, serialized)
                    else:
                        await with_retries(client.set, key, serialized)
                    success = True
                    logger.info(f"Successfully set Redis key: {key}")
                    return True
                except Exception as e:
                    logger.error(f"Error setting key {key} in Redis: {str(e)}")
        
        # If Redis fails, use memory cache
        _memory_cache[key] = value
        logger.info(f"Used memory cache for key {key}")
        success = True
            
    except Exception as e:
        logger.error(f"Error in set_with_fallback for key {key}: {str(e)}")
    
    return success

async def delete_with_fallback(key):
    """Delete a key from Redis with fallback to memory cache."""
    success = False
    
    try:
        async with redis_connection() as client:
            if client:
                try:
                    # Try to delete the key with retries
                    await with_retries(client.delete, key)
                    success = True
                    logger.info(f"Successfully deleted Redis key: {key}")
                except Exception as e:
                    logger.error(f"Error deleting key {key} from Redis: {str(e)}")
        
        # Always try to remove from memory cache regardless of Redis result
        if key in _memory_cache:
            del _memory_cache[key]
            logger.info(f"Deleted key {key} from memory cache")
            success = True
            
    except Exception as e:
        logger.error(f"Error in delete_with_fallback for key {key}: {str(e)}")
    
    return success

# In-memory fallback for list operations
_memory_lists = {}

async def list_append(key, value):
    """Append a value to a Redis list with retries and fallback."""
    success = False
    
    try:
        async with redis_connection() as client:
            if client:
                try:
                    # Try to append to the list with retries
                    await with_retries(client.rpush, key, value)
                    success = True
                    logger.info(f"Successfully appended to Redis list: {key}")
                    return True
                except Exception as e:
                    logger.error(f"Error appending to list {key} in Redis: {str(e)}")
        
        # If Redis fails, use memory list cache
        if key not in _memory_lists:
            _memory_lists[key] = []
        _memory_lists[key].append(value)
        logger.info(f"Used memory list cache for key {key}")
        success = True
            
    except Exception as e:
        logger.error(f"Error in list_append for key {key}: {str(e)}")
    
    return success

async def list_range(key, start=0, end=-1):
    """Get a range of values from a Redis list with retries and fallback."""
    try:
        async with redis_connection() as client:
            if client:
                try:
                    # Try to get the range with retries
                    values = await with_retries(client.lrange, key, start, end)
                    logger.info(f"Successfully retrieved Redis list range: {key}[{start}:{end}]")
                    return values
                except Exception as e:
                    logger.error(f"Error getting list range {key}[{start}:{end}] from Redis: {str(e)}")
        
        # If Redis fails, use memory list cache
        if key in _memory_lists:
            logger.info(f"Using memory list cache for key {key}")
            values = _memory_lists[key][start:None if end == -1 else end+1]
            return values
            
    except Exception as e:
        logger.error(f"Error in list_range for key {key}: {str(e)}")
    
    return []

async def get_redis_diagnostics() -> Dict[str, Any]:
    """
    Get detailed Redis diagnostic information.
    Useful for health check endpoints.
    
    Returns:
        Dict with diagnostic information including:
        - status: "connected", "error", or "unavailable"
        - error: Error message if applicable
        - backend: The Redis backend being used
        - version: Redis server version if available
        - memory_used: Memory used by Redis server if available
    """
    result = {
        "status": "unavailable",
        "error": None,
        "backend": redis_backend,
        "import_error": import_error,
        "url": redis_url_masked,
        "version": None,
        "memory_used": None,
        "clients_connected": None,
        "uptime_seconds": None,
        "using_mock": False
    }
    
    try:
        if redis is None:
            result["status"] = "error"
            result["error"] = f"Redis module not available: {import_error}"
            result["using_mock"] = True
            return result
        
        # Try to create a connection
        async with redis_connection() as client:
            if isinstance(client, MockRedis):
                result["status"] = "mock"
                result["error"] = "Using mock Redis implementation"
                result["using_mock"] = True
                result["version"] = "mock"
                return result
                
            # Test connection with ping
            ping_result = await client.ping()
            if not ping_result:
                result["status"] = "error"
                result["error"] = "Redis ping failed"
                return result
                
            # Connection is successful
            result["status"] = "connected"
            
            # Get Redis info for additional diagnostics
            try:
                info = await client.info()
                result["version"] = info.get("redis_version")
                result["memory_used"] = info.get("used_memory_human")
                result["clients_connected"] = info.get("connected_clients")
                result["uptime_seconds"] = info.get("uptime_in_seconds")
            except Exception as info_error:
                result["error"] = f"Connected but could not retrieve info: {info_error}"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc().split("\n")
    
    return result

# These functions can be exported for direct use
__all__ = [
    'redis_connection',
    'test_redis_connection',
    'get_with_fallback',
    'set_with_fallback',
    'delete_with_fallback',
    'MessageJSONEncoder',
    'get_redis_diagnostics'
] 