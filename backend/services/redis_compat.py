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

@contextlib.asynccontextmanager
async def redis_connection() -> AsyncGenerator[Optional[Any], None]:
    """
    Context manager for Redis connections to ensure proper cleanup.
    
    This creates an isolated connection for a single operation
    and guarantees it will be properly closed regardless of outcome.
    The function always returns either a real Redis client or a MockRedis instance,
    and properly handles cleanup in all cases.
    
    Usage:
        async with redis_connection() as client:
            # Use redis connection - guaranteed to be non-None
            await client.get("my_key")
    """
    client = None
    is_mock = False
    
    try:
        # Get Redis URL from environment or use default
        redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
        if not redis_url:
            logger.error("Redis URL not configured")
            client = MockRedis()
            is_mock = True
            yield client
        
        # Check if we have a real Redis module or we're using the fallback
        elif redis_backend in ("fallback", "fallback_final"):
            logger.error(f"Using fallback Redis implementation: {import_error}")
            client = MockRedis()
            is_mock = True
            yield client
            
        else:
            try:
                # Create the appropriate client based on the backend
                if redis_backend == "redis.asyncio":
                    # Modern redis.asyncio approach
                    try:
                        client = await redis.Redis.from_url(
                            redis_url,
                            decode_responses=True,
                            socket_timeout=3.0,
                            socket_connect_timeout=2.0,
                            retry_on_timeout=True
                        )
                        client_type = type(client).__name__
                        logger.debug(f"Created redis.asyncio client: {client_type}")
                    except Exception as e:
                        logger.error(f"Failed to create redis.asyncio client: {str(e)}")
                        logger.error(traceback.format_exc())
                        client = MockRedis()
                        is_mock = True
                
                elif redis_backend == "aioredis":
                    # Legacy aioredis approach
                    try:
                        client = await redis.from_url(
                            redis_url,
                            encoding="utf-8",
                            decode_responses=True,
                            socket_timeout=3.0,
                            socket_connect_timeout=2.0,
                            retry_on_timeout=True
                        )
                        client_type = type(client).__name__
                        logger.debug(f"Created aioredis client: {client_type}")
                    except Exception as e:
                        logger.error(f"Failed to create aioredis client: {str(e)}")
                        logger.error(traceback.format_exc())
                        client = MockRedis()
                        is_mock = True
                        
                else:
                    logger.error(f"Unsupported Redis backend: {redis_backend}")
                    client = MockRedis()
                    is_mock = True
                
                # If we got a client, validate it with ping
                if client and not is_mock:
                    try:
                        ping_result = await client.ping()
                        logger.debug(f"Redis PING result: {ping_result}")
                        # Client is valid, yield it
                        yield client
                    except Exception as e:
                        # Connection failed validation
                        logger.error(f"Redis connection validation failed: {e}")
                        logger.error(traceback.format_exc())
                        
                        # Clean up the failed connection - these operations are safer now
                        try:
                            if hasattr(client, 'close'):
                                # Detect if close is a coroutine function
                                if asyncio.iscoroutinefunction(getattr(client, 'close')):
                                    await client.close()
                                else:
                                    client.close()
                        except Exception as close_error:
                            logger.warning(f"Error closing invalid Redis connection: {close_error}")
                        
                        # Return a mock Redis client as a fallback
                        logger.warning("Creating a MockRedis instance due to validation failure")
                        client = MockRedis()
                        is_mock = True
                        yield client
                else:
                    # If client is None or already a mock, yield it
                    if client is None:
                        logger.error("Redis client creation returned None")
                        logger.warning("Creating a MockRedis instance due to null client")
                        client = MockRedis()
                        is_mock = True
                    
                    yield client
                    
            except Exception as connection_error:
                logger.error(f"Failed to create Redis client: {connection_error}")
                logger.error(traceback.format_exc())
                logger.warning("Creating a MockRedis instance due to connection failure")
                client = MockRedis()
                is_mock = True
                yield client
                
    except Exception as e:
        # Connection creation failed
        logger.error(f"Error creating Redis connection: {e}")
        logger.error(traceback.format_exc())
        logger.warning("Creating a MockRedis instance due to unexpected error")
        client = MockRedis()
        is_mock = True
        yield client
    finally:
        # Always ensure the connection is properly closed if it's a real client
        if client and not is_mock:
            try:
                # Safe cleanup that handles both redis.asyncio and aioredis
                client_type = type(client).__name__
                logger.debug(f"Closing Redis connection of type: {client_type}")
                
                # Different cleanup based on the actual client type
                if isinstance(client, MockRedis):
                    # MockRedis cleanup is a no-op
                    logger.debug("No cleanup needed for MockRedis")
                elif hasattr(client, '__class__') and hasattr(client.__class__, '__module__') and 'redis.asyncio' in getattr(client.__class__, '__module__', ''):
                    # redis.asyncio client
                    logger.debug("Detected redis.asyncio client, using async close()")
                    if hasattr(client, 'close'):
                        if asyncio.iscoroutinefunction(getattr(client, 'close')):
                            try:
                                await client.close()
                                logger.debug("Successfully closed redis.asyncio connection with async close()")
                            except Exception as e:
                                logger.warning(f"Error in redis.asyncio client close(): {e}")
                        else:
                            try:
                                client.close()
                                logger.debug("Successfully closed redis.asyncio connection with sync close()")
                            except Exception as e:
                                logger.warning(f"Error in redis.asyncio client sync close(): {e}")
                    else:
                        logger.warning(f"redis.asyncio client missing close() method: {client_type}")
                elif hasattr(client, '__class__') and hasattr(client.__class__, '__module__') and 'aioredis' in getattr(client.__class__, '__module__', ''):
                    # aioredis client
                    logger.debug("Detected aioredis client")
                    
                    # First try sync close if available
                    close_methods_attempted = []
                    close_success = False
                    wait_closed_success = False
                    
                    if hasattr(client, 'close'):
                        try:
                            if not asyncio.iscoroutinefunction(getattr(client, 'close')):
                                client.close()
                                logger.debug("Called sync close() on aioredis connection")
                                close_methods_attempted.append("sync close()")
                                close_success = True
                            else:
                                logger.debug("Skipping async close() for now, will try after wait_closed()")
                        except Exception as e:
                            logger.warning(f"Error in aioredis client close(): {e}")
                            close_methods_attempted.append("sync close() [failed]")
                    
                    # Then try wait_closed if available
                    if hasattr(client, 'wait_closed'):
                        try:
                            if asyncio.iscoroutinefunction(getattr(client, 'wait_closed')):
                                await client.wait_closed()
                                logger.debug("Successfully called wait_closed() on aioredis connection")
                                close_methods_attempted.append("wait_closed()")
                                wait_closed_success = True
                            else:
                                logger.warning("wait_closed() is not a coroutine function in aioredis client")
                                close_methods_attempted.append("wait_closed() [not async]")
                        except Exception as e:
                            logger.warning(f"Error in aioredis client wait_closed(): {e}")
                            close_methods_attempted.append("wait_closed() [failed]")
                    
                    # If we didn't run a sync close but have an async close, try that
                    if not close_success and hasattr(client, 'close') and asyncio.iscoroutinefunction(getattr(client, 'close')):
                        try:
                            await client.close()
                            logger.debug("Called async close() as fallback on aioredis connection")
                            close_methods_attempted.append("async close()")
                            close_success = True
                        except Exception as e:
                            logger.warning(f"Error in aioredis client async close(): {e}")
                            close_methods_attempted.append("async close() [failed]")
                    
                    # Try connection.close() if available (some aioredis clients expose this)
                    if not close_success and not wait_closed_success and hasattr(client, 'connection'):
                        if hasattr(client.connection, 'close'):
                            try:
                                if asyncio.iscoroutinefunction(getattr(client.connection, 'close')):
                                    await client.connection.close()
                                    logger.debug("Successfully called connection.close() on aioredis connection")
                                    close_methods_attempted.append("connection.close()")
                                    close_success = True
                                else:
                                    client.connection.close()
                                    logger.debug("Successfully called sync connection.close() on aioredis connection")
                                    close_methods_attempted.append("sync connection.close()")
                                    close_success = True
                            except Exception as e:
                                logger.warning(f"Error in aioredis client connection.close(): {e}")
                                close_methods_attempted.append("connection.close() [failed]")
                    
                    # Try _pool.close() if available (aioredis 1.x)
                    if not close_success and not wait_closed_success and hasattr(client, '_pool'):
                        if hasattr(client._pool, 'close'):
                            try:
                                if asyncio.iscoroutinefunction(getattr(client._pool, 'close')):
                                    await client._pool.close()
                                    logger.debug("Successfully called _pool.close() on aioredis connection")
                                    close_methods_attempted.append("_pool.close()")
                                    close_success = True
                                else:
                                    client._pool.close()
                                    logger.debug("Successfully called sync _pool.close() on aioredis connection") 
                                    close_methods_attempted.append("sync _pool.close()")
                                    close_success = True
                            except Exception as e:
                                logger.warning(f"Error in aioredis client _pool.close(): {e}")
                                close_methods_attempted.append("_pool.close() [failed]")
                    
                    if not close_success and not wait_closed_success:
                        logger.warning(f"Failed to close aioredis client with methods attempted: {', '.join(close_methods_attempted)}")
                        # Log client information to help debugging
                        logger.warning(f"Aioredis client type: {type(client).__name__}")
                        logger.warning(f"Available methods: {[m for m in dir(client) if not m.startswith('_') and callable(getattr(client, m))]}")
                        
                        # Last resort: try to call __del__ directly
                        if hasattr(client, '__del__'):
                            try:
                                client.__del__()
                                logger.debug("Successfully called __del__() on aioredis client")
                                close_success = True
                            except Exception as e:
                                logger.warning(f"Error calling __del__() on aioredis client: {e}")
                else:
                    # Generic attempt for unknown client types - try everything
                    logger.debug(f"Using generic close for unknown Redis client type: {client_type}")
                    
                    # Try the various close methods we know about
                    close_methods_tried = 0
                    
                    # Method 1: Try async close() if available
                    if hasattr(client, 'close'):
                        if asyncio.iscoroutinefunction(getattr(client, 'close')):
                            try:
                                await client.close()
                                logger.debug("Successfully called async close()")
                                close_methods_tried += 1
                            except Exception as e:
                                logger.warning(f"Error calling async close(): {e}")
                    
                    # Method 2: Try sync close() if available
                    if hasattr(client, 'close') and not asyncio.iscoroutinefunction(getattr(client, 'close')):
                        try:
                            client.close()
                            logger.debug("Successfully called sync close()")
                            close_methods_tried += 1
                        except Exception as e:
                            logger.warning(f"Error calling sync close(): {e}")
                    
                    # Method 3: Try wait_closed() if available
                    if hasattr(client, 'wait_closed'):
                        try:
                            if asyncio.iscoroutinefunction(getattr(client, 'wait_closed')):
                                await client.wait_closed()
                                logger.debug("Successfully called wait_closed()")
                                close_methods_tried += 1
                            else:
                                # Try sync wait_closed
                                client.wait_closed()
                                logger.debug("Successfully called sync wait_closed()")
                                close_methods_tried += 1
                        except Exception as e:
                            logger.warning(f"Error calling wait_closed(): {e}")
                    
                    # Method 4: Try aclose() if available (some libraries use this name)
                    if hasattr(client, 'aclose'):
                        try:
                            if asyncio.iscoroutinefunction(getattr(client, 'aclose')):
                                await client.aclose()
                                logger.debug("Successfully called aclose()")
                                close_methods_tried += 1
                            else:
                                # Try sync aclose
                                client.aclose()
                                logger.debug("Successfully called sync aclose()")
                                close_methods_tried += 1
                        except Exception as e:
                            logger.warning(f"Error calling aclose(): {e}")
                    
                    if close_methods_tried == 0:
                        logger.warning(f"Found no close methods for client type {client_type}")
            except Exception as e:
                # Log but don't re-raise - we don't want cleanup errors to propagate
                logger.warning(f"Unexpected error during Redis connection cleanup: {e}")
                logger.error(traceback.format_exc())

async def test_redis_connection() -> bool:
    """Test that Redis connection is working and log detailed diagnostic information."""
    try:
        logger.info(f"Testing Redis connection with backend: {redis_backend}")
        logger.info(f"Redis URL: {redis_url_masked}")
        
        if redis is None:
            logger.error(f"No Redis client available: {import_error}")
            return False
        
        # Try to create a connection
        async with redis_connection() as client:
            if isinstance(client, MockRedis):
                logger.warning("Using MockRedis instance - this is not a real Redis connection")
                return False
                
            # Test connection with ping
            result = await client.ping()
            logger.info(f"Redis PING result: {result}")
            
            # Log Redis info for debugging
            try:
                info = await client.info()
                logger.info(f"Redis version: {info.get('redis_version', 'unknown')}")
                logger.info(f"Redis server mode: {info.get('redis_mode', 'unknown')}")
                logger.info(f"Redis memory used: {info.get('used_memory_human', 'unknown')}")
            except Exception as info_error:
                logger.warning(f"Could not retrieve Redis info: {info_error}")
            
            return True
    except Exception as e:
        logger.error(f"Redis connection test failed with exception: {e}")
        logger.exception("Full stack trace for Redis connection failure:")
        return False

# Helper functions that maintain the same API regardless of underlying implementation

async def get_with_fallback(key: str) -> Optional[Any]:
    """Get a value from Redis with fallback to memory cache."""
    if not key:
        logger.warning("Attempted to get value with empty key")
        return None
        
    # Try Redis first
    try:
        async with redis_connection() as client:
            # The connection is guaranteed to return either a real client or MockRedis
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

async def set_with_fallback(key: str, value: Any, expiration: int = 86400) -> bool:
    """Set a value in Redis with fallback to memory cache."""
    if not key:
        logger.warning("Attempted to set value with empty key")
        return False
        
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
            # The connection is guaranteed to return either a real client or MockRedis
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
            
        return True
    except Exception as e:
        logger.error(f"Error setting {key} in memory cache: {e}")
        return redis_success  # Return Redis result if memory cache fails

async def delete_with_fallback(key: str) -> bool:
    """Delete a value from Redis with memory fallback cleanup."""
    if not key:
        logger.warning("Attempted to delete with empty key")
        return False
        
    redis_success = False
    try:
        async with redis_connection() as client:
            # The connection is guaranteed to return either a real client or MockRedis
            await client.delete(key)
            redis_success = True
    except Exception as e:
        logger.warning(f"Error deleting {key} from Redis: {e}")
    
    # Always clean up memory cache (regardless of Redis success)
    try:
        if key in _memory_cache:
            del _memory_cache[key]
    except Exception:
        pass
    
    return redis_success

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