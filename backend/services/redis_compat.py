"""
Redis Compatibility Layer

This module provides a compatibility layer for Redis operations using redis.asyncio.
It handles connection management and provides fallback mechanisms for serverless environments.
"""

import os
import logging
import redis.asyncio
from typing import Optional, Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory fallback cache
_memory_cache: Dict[str, Any] = {}

async def get_redis_client() -> Optional[redis.asyncio.Redis]:
    """Get a Redis client using redis.asyncio."""
    try:
        redis_url = os.environ.get("STORAGE_URL")
        if not redis_url:
            # Fall back to a Redis memory server for local development
            logger.warning("Redis URL not configured, using redis-memory server for local development")
            redis_url = "redis://localhost:6379/0"
            # Set the env var for other components to use
            os.environ["STORAGE_URL"] = redis_url

        client = redis.asyncio.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=3.0,
            socket_connect_timeout=2.0,
            retry_on_timeout=True
        )
        
        # Test connection
        await client.ping()
        logger.info("Redis connection successful")
        return client
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        return None

async def get_redis_diagnostics() -> Dict[str, Any]:
    """Get Redis connection diagnostics."""
    try:
        client = await get_redis_client()
        if client:
            info = await client.info()
            await client.close()
            return {
                "status": "connected",
                "backend": "redis.asyncio",
                "url_configured": bool(os.environ.get("STORAGE_URL")),
                "info": info
            }
    except Exception as e:
        logger.error(f"Redis diagnostics error: {e}")
    
    return {
        "status": "disconnected",
        "backend": "redis.asyncio",
        "url_configured": bool(os.environ.get("STORAGE_URL")),
        "error": str(e) if 'e' in locals() else "Unknown error"
    }

# Export the Redis client class for type hints
Redis = redis.asyncio.Redis 