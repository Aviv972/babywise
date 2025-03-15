"""
Vercel KV Service Bridge - Redirects to Redis Service

This file exists for backward compatibility with any code that was using vercel_kv_service.
All functionality is now provided by the redis_service module instead.
"""

import logging
from typing import Any, Optional

# Configure logging
logger = logging.getLogger(__name__)
logger.info("vercel_kv_service.py: Redirecting to redis_service.py for Redis operations")

# Import the new service
from backend.services.redis_service import (
    redis_service,
    get_redis,
    set_redis, 
    delete_redis,
    exists_redis,
    ping_redis
)

# Provide the same interface as before
class VercelKVService:
    """
    Bridge class that forwards operations to RedisService.
    """
    
    def __init__(self):
        """Initialize the bridge to redis_service."""
        self.client = redis_service.client
        logger.info("VercelKVService initialized as bridge to RedisService")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis via redis_service."""
        return await redis_service.get(key)
    
    async def set(self, key: str, value: Any, expiration: Optional[int] = None) -> bool:
        """Set a value in Redis via redis_service."""
        return await redis_service.set(key, value, expiration)
    
    async def delete(self, key: str) -> bool:
        """Delete a value from Redis via redis_service."""
        return await redis_service.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis via redis_service."""
        return await redis_service.exists(key)

# Create a singleton instance
vercel_kv_service = VercelKVService()

# Convenience functions that use the service
async def get_kv(key: str) -> Optional[Any]:
    """Get a value from Redis."""
    logger.debug(f"get_kv redirecting to get_redis for key: {key}")
    return await get_redis(key)

async def set_kv(key: str, value: Any, expiration: Optional[int] = None) -> bool:
    """Set a value in Redis."""
    logger.debug(f"set_kv redirecting to set_redis for key: {key}")
    return await set_redis(key, value, expiration)

async def delete_kv(key: str) -> bool:
    """Delete a value from Redis."""
    logger.debug(f"delete_kv redirecting to delete_redis for key: {key}")
    return await delete_redis(key)

async def exists_kv(key: str) -> bool:
    """Check if a key exists in Redis."""
    logger.debug(f"exists_kv redirecting to exists_redis for key: {key}")
    return await exists_redis(key) 