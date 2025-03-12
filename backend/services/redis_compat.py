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
    """Mock Redis implementation for when Redis is unavailable."""
    
    def __init__(self, *args, **kwargs):
        self._data = {}
        logger.warning("Created MockRedis instance - Redis functionality will be limited")
    
    async def ping(self):
        logger.info("MockRedis: PING called")
        return "PONG"
    
    async def get(self, key):
        logger.info(f"MockRedis: GET {key}")
        return self._data.get(key)
    
    async def set(self, key, value, ex=None):
        logger.info(f"MockRedis: SET {key} (expiry: {ex})")
        self._data[key] = value
        return True
    
    async def delete(self, key):
        logger.info(f"MockRedis: DELETE {key}")
        if key in self._data:
            del self._data[key]
            return 1
        return 0
    
    async def info(self):
        logger.info("MockRedis: INFO called")
        return {
            "redis_version": "mock",
            "redis_mode": "standalone",
            "used_memory_human": "0K",
            "connected_clients": "1",
            "uptime_in_seconds": "0"
        }
    
    async def close(self):
        logger.info("MockRedis: Connection closed")
        pass

# Determine which Redis client to use
USE_REDIS_ASYNCIO = os.environ.get("USE_REDIS_ASYNCIO", "True").lower() in ("true", "1", "yes")

# Import the appropriate Redis client
redis = None
redis_backend = "none"
import_error = None

try:
    if USE_REDIS_ASYNCIO:
        # Try modern approach with redis.asyncio
        try:
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
            redis = None
    
    # If redis.asyncio import failed or we're configured to use aioredis, try aioredis
    if redis is None:
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
            redis = None
except Exception as e:
    import_error = f"Unexpected error during Redis imports: {e}"
    logger.error(import_error)
    logger.error(traceback.format_exc())
    redis = None

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
    
    Works with both aioredis and redis.asyncio.
    
    Usage:
        async with redis_connection() as client:
            if client:
                # Use redis connection here
                await client.get("my_key")
    """
    client = None
    try:
        # Get Redis URL from environment or use default
        redis_url = os.environ.get("STORAGE_URL", REDIS_URL)
        if not redis_url:
            logger.error("Redis URL not configured")
            yield None
            return
        
        # Check if we have a real Redis module
        if redis is None:
            logger.error(f"No Redis client available: {import_error}")
            # Return a mock Redis client as a last resort
            logger.warning("Creating a MockRedis instance as a fallback")
            yield MockRedis()
            return
            
        try:
            if redis_backend == "redis.asyncio":
                # Modern redis.asyncio approach
                client = await redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=3.0,
                    socket_connect_timeout=2.0,
                    retry_on_timeout=True
                )
            elif redis_backend == "aioredis":
                # Legacy aioredis approach
                client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=3.0,
                    socket_connect_timeout=2.0,
                    retry_on_timeout=True
                )
            else:
                logger.error(f"Unsupported Redis backend: {redis_backend}")
                yield MockRedis()
                return
        except Exception as connection_error:
            logger.error(f"Failed to create Redis client: {connection_error}")
            logger.error(traceback.format_exc())
            # Return a mock Redis client as a last resort
            logger.warning("Creating a MockRedis instance due to connection failure")
            yield MockRedis()
            return
        
        try:
            # Validate connection with ping
            if client:
                await client.ping()
                # Connection is valid, yield it to the caller
                yield client
            else:
                logger.error("Redis client creation returned None")
                # Return a mock Redis client as a last resort
                logger.warning("Creating a MockRedis instance due to null client")
                yield MockRedis()
        except Exception as e:
            # Connection failed validation
            logger.error(f"Redis connection validation failed: {e}")
            logger.error(traceback.format_exc())
            # Clean up the failed connection
            if client:
                try:
                    if redis_backend == "redis.asyncio":
                        await client.close()  # redis.asyncio only needs close()
                    else:
                        client.close()
                        await client.wait_closed()  # aioredis needs both
                except Exception as ex:
                    logger.warning(f"Error closing invalid Redis connection: {ex}")
                client = None
            
            # Return a mock Redis client as a last resort
            logger.warning("Creating a MockRedis instance due to validation failure")
            yield MockRedis()
    except Exception as e:
        # Connection creation failed
        logger.error(f"Error creating Redis connection: {e}")
        logger.error(traceback.format_exc())
        # Return a mock Redis client as a last resort
        logger.warning("Creating a MockRedis instance due to unexpected error")
        yield MockRedis()
    finally:
        # Always ensure the connection is properly closed
        if client:
            try:
                if redis_backend == "redis.asyncio":
                    await client.close()  # redis.asyncio only needs close()
                elif redis_backend == "aioredis":
                    client.close()
                    await client.wait_closed()  # aioredis needs both
            except Exception as e:
                # Log but don't re-raise - we don't want cleanup errors to propagate
                logger.warning(f"Error closing Redis connection: {e}")

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
    # Try Redis first
    try:
        async with redis_connection() as client:
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
    redis_success = False
    try:
        async with redis_connection() as client:
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