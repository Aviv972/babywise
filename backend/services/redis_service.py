"""
Babywise Chatbot - Redis Service

This module provides Redis connection and operations for the Babywise Chatbot.
"""

import os
import json
import logging
import asyncio
import aioredis
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Connection timeout in seconds
REDIS_CONNECTION_TIMEOUT = 5.0

async def initialize_redis() -> Optional[aioredis.Redis]:
    """Initialize Redis connection with timeout"""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
        
    try:
        redis_url = os.getenv("STORAGE_URL")
        if not redis_url:
            logger.error("Redis URL not found in environment variables")
            return None
        
        # Log Redis connection attempt (without exposing credentials)
        masked_url = redis_url.replace(redis_url.split('@')[0], '***:***@')
        logger.info(f"Attempting to connect to Redis at {masked_url}")
        
        # Use asyncio.wait_for to add a timeout
        _redis_client = await asyncio.wait_for(
            aioredis.from_url(redis_url, socket_timeout=REDIS_CONNECTION_TIMEOUT),
            timeout=REDIS_CONNECTION_TIMEOUT
        )
        
        logger.info("Redis client initialized successfully")
        return _redis_client
    except asyncio.TimeoutError:
        logger.error(f"Redis connection timed out after {REDIS_CONNECTION_TIMEOUT} seconds")
        return None
    except Exception as e:
        logger.error(f"Error initializing Redis client: {str(e)}")
        return None

async def ensure_redis_initialized() -> bool:
    """Ensure Redis is initialized and ready for use"""
    try:
        redis = await initialize_redis()
        if redis is None:
            logger.warning("Redis client is None, initialization failed")
            return False
            
        # Test connection by pinging Redis with timeout
        try:
            await asyncio.wait_for(redis.ping(), timeout=2.0)
            logger.info("Redis ping successful")
            return True
        except asyncio.TimeoutError:
            logger.error("Redis ping timed out")
            return False
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error ensuring Redis is initialized: {str(e)}")
        return False

async def get_redis() -> Optional[aioredis.Redis]:
    """Get Redis client instance"""
    if _redis_client is None:
        return await initialize_redis()
    return _redis_client

async def set_cache(key: str, value: Any, expiration: int = 3600) -> bool:
    """Set a value in Redis cache"""
    try:
        redis = await get_redis()
        if not redis:
            return False
            
        value_json = json.dumps(value)
        await redis.set(key, value_json, ex=expiration)
        return True
    except Exception as e:
        logger.error(f"Error setting cache: {str(e)}")
        return False

async def get_cache(key: str) -> Optional[Any]:
    """Get a value from Redis cache"""
    try:
        redis = await get_redis()
        if not redis:
            return None
            
        value = await redis.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Error getting cache: {str(e)}")
        return None

async def delete_cache(key: str) -> bool:
    """Delete a value from Redis cache"""
    try:
        redis = await get_redis()
        if not redis:
            return False
            
        await redis.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error deleting cache: {str(e)}")
        return False

# Thread state operations
async def get_thread_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get thread state from Redis"""
    key = f"{THREAD_STATE_PREFIX}{thread_id}"
    return await get_cache(key)

async def save_thread_state(thread_id: str, state: Dict[str, Any]) -> bool:
    """Save thread state to Redis"""
    key = f"{THREAD_STATE_PREFIX}{thread_id}"
    return await set_cache(key, state, THREAD_STATE_EXPIRATION)

async def delete_thread_state(thread_id: str) -> bool:
    """Delete thread state from Redis"""
    key = f"{THREAD_STATE_PREFIX}{thread_id}"
    return await delete_cache(key)

# Routine-specific cache operations
async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """Cache a routine summary"""
    key = f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}"
    return await set_cache(key, summary, SUMMARY_EXPIRATION)

async def get_cached_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get a cached routine summary"""
    key = f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}"
    return await get_cache(key)

async def cache_recent_events(thread_id: str, routine_type: str, events: List[Dict[str, Any]]) -> bool:
    """Cache recent routine events"""
    key = f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}"
    return await set_cache(key, events, RECENT_EVENTS_EXPIRATION)

async def get_cached_recent_events(thread_id: str, routine_type: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached recent events"""
    key = f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}"
    return await get_cache(key)

async def cache_active_routine(thread_id: str, routine_type: str, routine_data: Dict[str, Any]) -> bool:
    """Cache an active routine"""
    key = f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
    return await set_cache(key, routine_data, ACTIVE_ROUTINE_EXPIRATION)

async def get_active_routine(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """Get an active routine"""
    key = f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
    return await get_cache(key)

async def invalidate_routine_cache(thread_id: str, routine_type: str) -> bool:
    """Invalidate all cached data for a routine type"""
    try:
        keys = [
            f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}",
            f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}",
            f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
        ]
        
        for key in keys:
            await delete_cache(key)
        return True
    except Exception as e:
        logger.error(f"Error invalidating routine cache: {str(e)}")
        return False 