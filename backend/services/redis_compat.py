"""
Redis Compatibility Layer

This module provides a compatibility layer for Redis operations using redis.asyncio via redis_service.
It handles connection management and provides fallback mechanisms for serverless environments.
"""

import os
import logging
from typing import Optional, Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import redis service instead of creating a new connection
from backend.services.redis_service import redis_service, ping_redis

async def get_redis_client() -> Optional[Any]:
    """
    Get a Redis client using the redis_service singleton.
    
    Returns the existing client from redis_service instead of creating a new connection.
    This ensures connection reuse and better performance in serverless environments.
    """
    try:
        # Check if UPSTASH_REDIS_URL or STORAGE_URL is configured
        redis_url = os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("STORAGE_URL")
        if not redis_url:
            # Fall back to a Redis memory server for local development
            logger.warning("Redis URL not configured, using redis-memory server for local development")
            redis_url = "redis://localhost:6379/0"
            # Set the env vars for other components to use
            os.environ["STORAGE_URL"] = redis_url
            os.environ["UPSTASH_REDIS_URL"] = redis_url

        # Use the existing client from redis_service
        if redis_service.client is not None:
            logger.debug("Using existing Redis client from redis_service")
            return redis_service.client
        else:
            logger.warning("Redis client not available from redis_service")
            return None
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        return None

async def get_redis_diagnostics() -> Dict[str, Any]:
    """
    Get Redis connection diagnostics using the redis_service.
    
    This calls the detailed diagnostics function from index.py.
    """
    try:
        # Import the function from index.py where it's now defined
        from backend.api.index import get_redis_diagnostics as get_detailed_diagnostics
        
        # Call the detailed diagnostics function
        return await get_detailed_diagnostics()
    except ImportError:
        # Fallback if the import fails
        logger.warning("Could not import get_redis_diagnostics from backend.api.index, using fallback")
        
        try:
            # Run a basic diagnostics with available info
            client = await get_redis_client()
            is_connected = await ping_redis()
            
            return {
                "status": "connected" if is_connected else "disconnected",
                "backend": "redis.asyncio via redis_service",
                "url_configured": bool(os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("STORAGE_URL")),
                "client_available": client is not None
            }
        except Exception as e:
            logger.error(f"Redis diagnostics error: {e}")
        
        return {
            "status": "error",
            "backend": "redis.asyncio via redis_service",
            "url_configured": bool(os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("STORAGE_URL")),
            "error": str(e) if 'e' in locals() else "Unknown error"
        }

# Export the Redis client class for type hints
import redis.asyncio
Redis = redis.asyncio.Redis 