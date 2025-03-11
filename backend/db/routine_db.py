#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database module for handling routine events
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from backend.services.redis_service import get_redis, RedisKeyPrefix

logger = logging.getLogger(__name__)

async def add_event(
    thread_id: str,
    event_type: str,
    event_time: str,
    event_data: Optional[Dict[str, Any]] = None,
    local_id: Optional[str] = None
) -> Dict[str, Any]:
    """Add a routine event to the database."""
    try:
        redis = await get_redis()
        
        # Create event object
        event = {
            "thread_id": thread_id,
            "event_type": event_type,
            "event_time": event_time,
            "event_data": event_data or {},
            "local_id": local_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Generate key for the event
        event_key = f"{RedisKeyPrefix.EVENT}:{thread_id}:{event_type}:{event_time}"
        
        # Store event in Redis
        await redis.set(event_key, json.dumps(event))
        
        # Add to thread's event list
        thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
        await redis.rpush(thread_events_key, event_key)
        
        return event
        
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        raise

async def get_events(
    thread_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get routine events from the database."""
    try:
        redis = await get_redis()
        events = []
        
        # If thread_id is provided, get events for that thread
        if thread_id:
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            event_keys = await redis.lrange(thread_events_key, 0, -1)
            
            for event_key in event_keys:
                event_json = await redis.get(event_key)
                if event_json:
                    event = json.loads(event_json)
                    event_time = datetime.fromisoformat(event["event_time"].replace("Z", "+00:00"))
                    
                    # Apply date filters if provided
                    if start_date:
                        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                        if event_time < start:
                            continue
                    
                    if end_date:
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        if event_time > end:
                            continue
                    
                    events.append(event)
        
        return sorted(events, key=lambda x: x["event_time"])
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise

async def get_latest_event(thread_id: str, event_type: str) -> Optional[Dict[str, Any]]:
    """Get the latest event of a specific type for a thread."""
    try:
        events = await get_events(thread_id=thread_id)
        matching_events = [e for e in events if e["event_type"] == event_type]
        
        if matching_events:
            return max(matching_events, key=lambda x: x["event_time"])
        return None
        
    except Exception as e:
        logger.error(f"Error getting latest event: {e}")
        raise

async def get_summary(thread_id: str, period: str = "day") -> Dict[str, Any]:
    """Get a summary of routine events for a thread."""
    try:
        # Calculate time range based on period
        now = datetime.utcnow()
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now - timedelta(days=1)
        
        # Get events for the period
        events = await get_events(
            thread_id=thread_id,
            start_date=start_date.isoformat(),
            end_date=now.isoformat()
        )
        
        # Process sleep events
        sleep_events = [e for e in events if e["event_type"] == "sleep"]
        sleep_end_events = [e for e in events if e["event_type"] == "sleep_end"]
        
        total_sleep_duration = 0
        sleep_periods = []
        
        for sleep_event in sleep_events:
            sleep_start = datetime.fromisoformat(sleep_event["event_time"].replace("Z", "+00:00"))
            
            # Find matching end event
            matching_end = next(
                (e for e in sleep_end_events if datetime.fromisoformat(e["event_time"].replace("Z", "+00:00")) > sleep_start),
                None
            )
            
            if matching_end:
                sleep_end = datetime.fromisoformat(matching_end["event_time"].replace("Z", "+00:00"))
                duration = int((sleep_end - sleep_start).total_seconds() / 60)  # Duration in minutes
                total_sleep_duration += duration
                
                sleep_periods.append({
                    "start": sleep_event["event_time"],
                    "end": matching_end["event_time"],
                    "duration": duration
                })
        
        # Process feed events
        feed_events = [e for e in events if e["event_type"] == "feed"]
        
        return {
            "sleep": {
                "total_duration": total_sleep_duration,
                "events": sleep_periods
            },
            "feed": {
                "total_count": len(feed_events),
                "events": feed_events
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise 