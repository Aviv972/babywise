"""
Redis Service for Upstash Redis access using the standard redis-py package.
This provides a higher-level interface to the Redis connection.
"""

import os
import logging
import json
import traceback
from typing import Any, Dict, List, Optional, Union

try:
    import redis.asyncio
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("redis.asyncio package not available, using memory cache only")

# Configure logging
logger = logging.getLogger(__name__)

# In-memory fallback cache when Redis is unavailable
_memory_cache = {}

class RedisService:
    """
    Service for interacting with Redis (optimized for Upstash Redis).
    Provides common operations and handles connection errors with fallbacks.
    """
    
    def __init__(self):
        """Initialize the Redis service."""
        self.client = None
        if REDIS_AVAILABLE:
            try:
                # Try Upstash URL first, fall back to STORAGE_URL
                redis_url = os.environ.get("UPSTASH_REDIS_URL")
                if not redis_url:
                    redis_url = os.environ.get("STORAGE_URL")
                    
                if not redis_url:
                    logger.error("No Redis URL found in environment variables")
                    return
                    
                logger.info(f"Initializing Redis client with URL: {redis_url.split('@')[0]}@...")
                
                self.client = redis.asyncio.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=3.0,
                    socket_connect_timeout=2.0,
                    retry_on_timeout=True
                )
                logger.info("Redis client initialized")
            except Exception as e:
                logger.error(f"Error initializing Redis client: {e}")
                logger.error(traceback.format_exc())
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        Falls back to memory cache if Redis is unavailable.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value if found, or None
        """
        if not key:
            logger.warning("Attempted to get with empty key")
            return None
            
        logger.debug(f"Getting value for key: {key}")
        
        try:
            if self.client:
                # Try to get from Redis
                value = await self.client.get(key)
                
                if value is not None:
                    logger.debug(f"Got value from Redis for key: {key}")
                    
                    # Try to parse JSON if it looks like JSON
                    if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return value
                    return value
                else:
                    logger.debug(f"No value found in Redis for key: {key}")
            else:
                logger.warning("Redis client not available")
        except Exception as e:
            logger.error(f"Error getting value from Redis for key {key}: {e}")
        
        # Fall back to memory cache
        if key in _memory_cache:
            logger.info(f"Using memory cache fallback for key: {key}")
            return _memory_cache.get(key)
        
        logger.debug(f"No value found for key: {key}")
        return None
    
    async def set(self, key: str, value: Any, expiration: Optional[int] = None) -> bool:
        """
        Set a value in Redis.
        Always updates memory cache regardless of Redis availability.
        
        Args:
            key: The key to set
            value: The value to store
            expiration: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not key:
            logger.warning("Attempted to set with empty key")
            return False
            
        logger.debug(f"Setting value for key: {key}")
        
        # Convert complex objects to JSON strings for storage
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        
        success = False
        try:
            if self.client:
                # Try to set in Redis
                if expiration:
                    await self.client.set(key, value, ex=expiration)
                else:
                    await self.client.set(key, value)
                logger.debug(f"Value set in Redis for key: {key}")
                success = True
            else:
                logger.warning("Redis client not available for setting value")
        except Exception as e:
            logger.error(f"Error setting value in Redis for key {key}: {e}")
        
        # Always update memory cache
        try:
            # For memory cache, store already parsed objects if possible
            if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                try:
                    _memory_cache[key] = json.loads(value)
                except json.JSONDecodeError:
                    _memory_cache[key] = value
            else:
                _memory_cache[key] = value
                
            logger.debug(f"Value set in memory cache for key: {key}")
            
            # We consider it a success if at least the memory cache was updated
            return True
        except Exception as e:
            logger.error(f"Error setting value in memory cache for key {key}: {e}")
            return success
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from Redis.
        Always tries to delete from memory cache regardless of Redis availability.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not key:
            logger.warning("Attempted to delete with empty key")
            return False
            
        logger.debug(f"Deleting key: {key}")
        
        success = False
        try:
            if self.client:
                # Try to delete from Redis
                await self.client.delete(key)
                logger.debug(f"Key deleted from Redis: {key}")
                success = True
            else:
                logger.warning("Redis client not available for deleting key")
        except Exception as e:
            logger.error(f"Error deleting key from Redis: {key}, error: {e}")
        
        # Always try to delete from memory cache
        try:
            if key in _memory_cache:
                del _memory_cache[key]
                logger.debug(f"Key deleted from memory cache: {key}")
                
            # We consider it a success if at least we got here without errors
            return True
        except Exception as e:
            logger.error(f"Error deleting key from memory cache: {key}, error: {e}")
            return success
            
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        Falls back to memory cache if Redis is unavailable.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        if not key:
            logger.warning("Attempted to check existence with empty key")
            return False
            
        logger.debug(f"Checking if key exists: {key}")
        
        try:
            if self.client:
                # Try to check in Redis
                exists = await self.client.exists(key)
                logger.debug(f"Key {key} exists in Redis: {exists}")
                return exists == 1
            else:
                logger.warning("Redis client not available for checking key existence")
        except Exception as e:
            logger.error(f"Error checking if key exists in Redis: {key}, error: {e}")
        
        # Fall back to memory cache
        exists = key in _memory_cache
        logger.debug(f"Key {key} exists in memory cache: {exists}")
        return exists

    async def ping(self) -> bool:
        """
        Check if Redis is responsive.
        
        Returns:
            True if Redis responds to ping, False otherwise
        """
        try:
            if self.client:
                response = await self.client.ping()
                return response
            return False
        except Exception as e:
            logger.error(f"Error pinging Redis: {e}")
            return False

# Create a singleton instance
redis_service = RedisService()

# Convenience functions that use the service
async def get_redis(key: str) -> Optional[Any]:
    """Get a value from Redis."""
    return await redis_service.get(key)

async def set_redis(key: str, value: Any, expiration: Optional[int] = None) -> bool:
    """Set a value in Redis."""
    return await redis_service.set(key, value, expiration)

async def delete_redis(key: str) -> bool:
    """Delete a value from Redis."""
    return await redis_service.delete(key)

async def exists_redis(key: str) -> bool:
    """Check if a key exists in Redis."""
    return await redis_service.exists(key)

async def ping_redis() -> bool:
    """Check if Redis is responsive."""
    return await redis_service.ping() 