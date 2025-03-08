"""
Babywise Chatbot - Analytics Service

This module provides Redis-based analytics for routine tracking,
storing and retrieving aggregated statistics for baby routines.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.services.redis_service import initialize_redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analytics key prefixes
DAILY_STATS_PREFIX = "analytics:daily:"
WEEKLY_STATS_PREFIX = "analytics:weekly:"
PATTERN_STATS_PREFIX = "analytics:patterns:"

# Cache expiration times (in seconds)
DAILY_STATS_EXPIRATION = 86400  # 24 hours
WEEKLY_STATS_EXPIRATION = 604800  # 7 days
PATTERN_STATS_EXPIRATION = 2592000  # 30 days

async def update_daily_stats(thread_id: str, routine_type: str, stats: Dict[str, Any]) -> bool:
    """
    Update daily statistics for a specific routine type.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        stats: Statistics to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return False
            
        # Create key with date
        today = datetime.utcnow().date().isoformat()
        cache_key = f"{DAILY_STATS_PREFIX}{thread_id}:{routine_type}:{today}"
        
        # Get existing stats
        existing_stats = await redis_client.get(cache_key)
        if existing_stats:
            existing_stats = json.loads(existing_stats)
            # Merge new stats with existing stats
            for key, value in stats.items():
                if key in existing_stats:
                    if isinstance(value, (int, float)):
                        if key == "average_duration":
                            # Recalculate average duration
                            total_events = existing_stats["total_events"] + stats["total_events"]
                            total_duration = (
                                existing_stats["total_duration_hours"] + stats["total_duration_hours"]
                            )
                            existing_stats[key] = total_duration / total_events
                        else:
                            existing_stats[key] += value
                    elif isinstance(value, list):
                        existing_stats[key].extend(value)
                    else:
                        existing_stats[key] = value
                else:
                    existing_stats[key] = value
            stats = existing_stats
        
        # Save updated stats
        stats_json = json.dumps(stats)
        result = await redis_client.set(cache_key, stats_json, ex=DAILY_STATS_EXPIRATION)
        logger.info(f"Updated daily stats for {routine_type} (thread {thread_id}): {result}")
        return bool(result)
    except Exception as e:
        logger.error(f"Error updating daily stats: {str(e)}")
        return False

async def get_daily_stats(thread_id: str, routine_type: str, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """
    Get daily statistics for a specific routine type.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        date: The date to get stats for (defaults to today)
        
    Returns:
        Statistics dictionary or None if not found
    """
    try:
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return None
            
        # Use provided date or today
        stats_date = (date or datetime.utcnow()).date().isoformat()
        cache_key = f"{DAILY_STATS_PREFIX}{thread_id}:{routine_type}:{stats_date}"
        
        # Get stats from Redis
        stats_json = await redis_client.get(cache_key)
        if stats_json:
            logger.info(f"Retrieved daily stats for {routine_type} (thread {thread_id})")
            return json.loads(stats_json)
            
        logger.info(f"No daily stats found for {routine_type} (thread {thread_id})")
        return None
    except Exception as e:
        logger.error(f"Error retrieving daily stats: {str(e)}")
        return None

async def update_weekly_stats(thread_id: str, routine_type: str, stats: Dict[str, Any]) -> bool:
    """
    Update weekly statistics for a specific routine type.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        stats: Statistics to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return False
            
        # Create key with week number
        today = datetime.utcnow()
        week = today.strftime("%Y-W%W")  # Format: YYYY-WNN
        cache_key = f"{WEEKLY_STATS_PREFIX}{thread_id}:{routine_type}:{week}"
        
        # Get existing stats
        existing_stats = await redis_client.get(cache_key)
        if existing_stats:
            existing_stats = json.loads(existing_stats)
            # Merge new stats with existing stats
            for key, value in stats.items():
                if key in existing_stats:
                    if isinstance(value, (int, float)):
                        if key == "average_duration":
                            # Recalculate average duration
                            total_events = existing_stats["total_events"] + stats["total_events"]
                            total_duration = (
                                existing_stats["total_duration_hours"] + stats["total_duration_hours"]
                            )
                            existing_stats[key] = total_duration / total_events
                        elif key == "days_tracked":
                            # Don't double count days
                            existing_stats[key] = max(existing_stats[key], value)
                        else:
                            existing_stats[key] += value
                    elif isinstance(value, list):
                        existing_stats[key].extend(value)
                    else:
                        existing_stats[key] = value
                else:
                    existing_stats[key] = value
            stats = existing_stats
        
        # Save updated stats
        stats_json = json.dumps(stats)
        result = await redis_client.set(cache_key, stats_json, ex=WEEKLY_STATS_EXPIRATION)
        logger.info(f"Updated weekly stats for {routine_type} (thread {thread_id}): {result}")
        return bool(result)
    except Exception as e:
        logger.error(f"Error updating weekly stats: {str(e)}")
        return False

async def get_weekly_stats(thread_id: str, routine_type: str, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """
    Get weekly statistics for a specific routine type.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        date: Any date in the week to get stats for (defaults to current week)
        
    Returns:
        Statistics dictionary or None if not found
    """
    try:
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return None
            
        # Use provided date or today to get week number
        stats_date = date or datetime.utcnow()
        week = stats_date.strftime("%Y-W%W")
        cache_key = f"{WEEKLY_STATS_PREFIX}{thread_id}:{routine_type}:{week}"
        
        # Get stats from Redis
        stats_json = await redis_client.get(cache_key)
        if stats_json:
            logger.info(f"Retrieved weekly stats for {routine_type} (thread {thread_id})")
            return json.loads(stats_json)
            
        logger.info(f"No weekly stats found for {routine_type} (thread {thread_id})")
        return None
    except Exception as e:
        logger.error(f"Error retrieving weekly stats: {str(e)}")
        return None

async def update_pattern_stats(thread_id: str, routine_type: str, pattern: Dict[str, Any]) -> bool:
    """
    Update pattern statistics for routine analysis.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        pattern: Pattern data to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return False
            
        cache_key = f"{PATTERN_STATS_PREFIX}{thread_id}:{routine_type}"
        logger.info(f"Updating pattern stats for key {cache_key}")
        logger.info(f"Input pattern: {pattern}")
        
        # Get existing patterns
        existing_patterns = await redis_client.get(cache_key)
        if existing_patterns:
            existing_patterns = json.loads(existing_patterns)
            logger.info(f"Existing patterns: {existing_patterns}")
            
            # Update pattern frequencies
            for key, value in pattern.items():
                if key in existing_patterns:
                    if isinstance(value, dict):
                        if key not in existing_patterns:
                            existing_patterns[key] = {}
                        for subkey, subvalue in value.items():
                            if subvalue > 0:  # Only add if the new value is positive
                                if subkey in existing_patterns[key]:
                                    if key == "time_ranges":
                                        # For time ranges, we want to preserve all occurrences
                                        if subvalue > 0:
                                            existing_patterns[key][subkey] = 1
                                    else:
                                        # For other stats, we want to accumulate
                                        existing_patterns[key][subkey] += subvalue
                                else:
                                    existing_patterns[key][subkey] = subvalue
                                logger.info(f"Updated {key}.{subkey} to {existing_patterns[key][subkey]}")
                    elif isinstance(value, (int, float)):
                        if value > 0:  # Only add if the new value is positive
                            existing_patterns[key] += value
                            logger.info(f"Updated {key} to {existing_patterns[key]}")
                    else:
                        existing_patterns[key] = value
                        logger.info(f"Set {key} to {value}")
                else:
                    existing_patterns[key] = value
                    logger.info(f"Added new key {key} with value {value}")
            pattern = existing_patterns
        else:
            # Initialize pattern structure if it doesn't exist
            pattern = {
                "time_ranges": {
                    "morning": pattern.get("time_ranges", {}).get("morning", 0),
                    "afternoon": pattern.get("time_ranges", {}).get("afternoon", 0),
                    "night": pattern.get("time_ranges", {}).get("night", 0)
                },
                "durations": {
                    "short": pattern.get("durations", {}).get("short", 0),
                    "long": pattern.get("durations", {}).get("long", 0)
                }
            }
            logger.info(f"Initialized new pattern structure: {pattern}")
        
        # Save updated patterns
        pattern_json = json.dumps(pattern)
        result = await redis_client.set(cache_key, pattern_json, ex=PATTERN_STATS_EXPIRATION)
        logger.info(f"Updated pattern stats for {routine_type} (thread {thread_id}): {result}")
        logger.info(f"Final pattern: {pattern}")
        return bool(result)
    except Exception as e:
        logger.error(f"Error updating pattern stats: {str(e)}")
        return False

async def get_pattern_stats(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """
    Get pattern statistics for routine analysis.
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        
    Returns:
        Pattern statistics dictionary or None if not found
    """
    try:
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return None
            
        cache_key = f"{PATTERN_STATS_PREFIX}{thread_id}:{routine_type}"
        
        # Get patterns from Redis
        pattern_json = await redis_client.get(cache_key)
        if pattern_json:
            logger.info(f"Retrieved pattern stats for {routine_type} (thread {thread_id})")
            return json.loads(pattern_json)
            
        logger.info(f"No pattern stats found for {routine_type} (thread {thread_id})")
        return None
    except Exception as e:
        logger.error(f"Error retrieving pattern stats: {str(e)}")
        return None 