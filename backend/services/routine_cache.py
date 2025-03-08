"""
Babywise Chatbot - Routine Cache Service

This module provides Redis caching for routine data, improving performance
by caching frequently accessed routine information and summaries.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.services.redis_service import (
    ensure_redis_initialized,
    set_cache,
    get_cache,
    delete_cache,
    ROUTINE_SUMMARY_PREFIX,
    RECENT_EVENTS_PREFIX,
    ACTIVE_ROUTINE_PREFIX,
    SUMMARY_EXPIRATION,
    RECENT_EVENTS_EXPIRATION,
    ACTIVE_ROUTINE_EXPIRATION
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cache_routine_summary(thread_id: str, routine_type: str, summary: Dict[str, Any]) -> bool:
    """
    Cache a routine summary for quick access.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        summary: Summary data to cache
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return False
            
        cache_key = f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}"
        result = await set_cache(cache_key, summary, SUMMARY_EXPIRATION)
        logger.info(f"Cached {routine_type} summary for thread {thread_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error caching routine summary: {str(e)}")
        return False

async def get_cached_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a cached routine summary.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        
    Returns:
        Cached summary or None if not found
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return None
            
        cache_key = f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}"
        result = await get_cache(cache_key)
        
        if result:
            logger.info(f"Retrieved cached {routine_type} summary for thread {thread_id}")
            return result
            
        logger.info(f"No cached {routine_type} summary found for thread {thread_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached routine summary: {str(e)}")
        return None

async def cache_recent_events(thread_id: str, routine_type: str, events: List[Dict[str, Any]]) -> bool:
    """
    Cache recent routine events.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        events: List of recent events to cache
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return False
            
        cache_key = f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}"
        result = await set_cache(cache_key, events, RECENT_EVENTS_EXPIRATION)
        logger.info(f"Cached {len(events)} {routine_type} events for thread {thread_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error caching recent events: {str(e)}")
        return False

async def get_cached_recent_events(thread_id: str, routine_type: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve cached recent events.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        
    Returns:
        List of cached events or None if not found
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return None
            
        cache_key = f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}"
        result = await get_cache(cache_key)
        
        if result:
            logger.info(f"Retrieved cached {routine_type} events for thread {thread_id}")
            return result
            
        logger.info(f"No cached {routine_type} events found for thread {thread_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached events: {str(e)}")
        return None

async def cache_active_routine(thread_id: str, routine_type: str, routine_data: Dict[str, Any]) -> bool:
    """
    Cache an active (in-progress) routine.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        routine_data: Data about the active routine
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return False
            
        cache_key = f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
        result = await set_cache(cache_key, routine_data, ACTIVE_ROUTINE_EXPIRATION)
        logger.info(f"Cached active {routine_type} routine for thread {thread_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error caching active routine: {str(e)}")
        return False

async def get_active_routine(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve an active (in-progress) routine.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        
    Returns:
        Active routine data or None if not found
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return None
            
        cache_key = f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
        result = await get_cache(cache_key)
        
        if result:
            logger.info(f"Retrieved active {routine_type} routine for thread {thread_id}")
            return result
            
        logger.info(f"No active {routine_type} routine found for thread {thread_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving active routine: {str(e)}")
        return None

async def invalidate_routine_cache(thread_id: str, routine_type: str) -> bool:
    """
    Invalidate all cached data for a specific routine type.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not await ensure_redis_initialized():
            logger.error("Failed to initialize Redis")
            return False
            
        # Delete all cache entries for this routine type
        keys_to_delete = [
            f"{ROUTINE_SUMMARY_PREFIX}{thread_id}:{routine_type}",
            f"{RECENT_EVENTS_PREFIX}{thread_id}:{routine_type}",
            f"{ACTIVE_ROUTINE_PREFIX}{thread_id}:{routine_type}"
        ]
        
        success = True
        for key in keys_to_delete:
            result = await delete_cache(key)
            logger.info(f"Deleted cache key {key}: {result}")
            success = success and result
            
        logger.info(f"Invalidated cache for {routine_type} routine (thread {thread_id})")
        return success
    except Exception as e:
        logger.error(f"Error invalidating routine cache: {str(e)}")
        return False 