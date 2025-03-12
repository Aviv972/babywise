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
from typing import Optional, Dict, Any, List, AsyncGenerator, Union
from datetime import datetime

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Determine which Redis client to use
USE_REDIS_ASYNCIO = True  # Set to True to use redis.asyncio, False for aioredis

try:
    if USE_REDIS_ASYNCIO:
        # Modern approach with redis.asyncio
        logger.info("Using redis.asyncio for Redis operations")
        from redis import asyncio as redis
        from redis.exceptions import (
            AuthenticationError, 
            ConnectionError,
            TimeoutError,
            ResponseError,
            DataError
        )
    else:
        # Legacy approach with aioredis
        logger.info("Using aioredis for Redis operations")
        import aioredis as redis
        from aioredis.exceptions import (
            AuthenticationError, 
            ConnectionError,
            TimeoutError,
            ResponseError,
            DataError
        )
except ImportError as e:
    logger.error(f"Failed to import Redis package: {e}")
    # Create fallback exception classes
    class RedisError(Exception): pass
    class ConnectionError(RedisError): pass
    class TimeoutError(RedisError): pass
    class AuthenticationError(ConnectionError): pass
    class ResponseError(RedisError): pass
    class DataError(RedisError): pass

# Redis connection configuration
REDIS_URL = os.environ.get("STORAGE_URL", "redis://localhost:6379/0")

# In-memory fallback cache when Redis is unavailable
_memory_cache: Dict[str, Any] = {}

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
            
        if USE_REDIS_ASYNCIO:
            # Modern redis.asyncio approach
            client = await redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=3.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=True
            )
        else:
            # Legacy aioredis approach
            client = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=3.0,
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
                    if USE_REDIS_ASYNCIO:
                        await client.close()  # redis.asyncio only needs close()
                    else:
                        client.close()
                        await client.wait_closed()  # aioredis needs both
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
                if USE_REDIS_ASYNCIO:
                    await client.close()  # redis.asyncio only needs close()
                else:
                    client.close()
                    await client.wait_closed()  # aioredis needs both
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

# Helper functions that maintain the same API regardless of underlying implementation

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
    
    # Always clean up memory cache (regardless of Redis success)
    try:
        if key in _memory_cache:
            del _memory_cache[key]
    except Exception:
        pass
    
    return redis_success

# These functions can be exported for direct use
__all__ = [
    'redis_connection',
    'test_redis_connection',
    'get_with_fallback',
    'set_with_fallback',
    'delete_with_fallback',
    'MessageJSONEncoder'
] 