#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database module for handling routine events
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from backend.services.redis_service import get_redis, RedisKeyPrefix, get_with_fallback, set_with_fallback

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
        # Get Redis connection
        redis = await get_redis()
        if redis is None:
            logger.error("Failed to get Redis connection for adding event")
            raise Exception("Redis connection failed")
        
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
        event_id = f"{event_time.replace(':', '-').replace('.', '-')}-{local_id or event_type}"
        event_key = f"{RedisKeyPrefix.EVENT}:{thread_id}:{event_type}:{event_id}"
        
        # Store event in Redis
        try:
            # Convert to JSON
            event_json = json.dumps(event)
            await redis.set(event_key, event_json)
            
            # Add to thread's event list
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            await redis.rpush(thread_events_key, event_key)
            
            logger.info(f"Successfully added {event_type} event for thread {thread_id}")
            return event
        except Exception as e:
            logger.error(f"Redis operation failed while adding event: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        # Return a partial event with error info for better debugging
        return {
            "thread_id": thread_id,
            "event_type": event_type,
            "event_time": event_time,
            "error": str(e),
            "status": "failed"
        }

async def get_events(
    thread_id: str,
    event_type: Optional[str] = None,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None
) -> List[Dict[str, Any]]:
    """Get routine events with robust error handling."""
    logger.info(f"Getting events for thread {thread_id} with filters: type={event_type}, start={start_date}, end={end_date}")
    
    try:
        # Get Redis connection
        redis = await get_redis()
        if not redis:
            logger.error("Failed to get Redis connection for retrieving events")
            return []
        
        # Get the thread's event keys
        thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
        event_keys = await redis.lrange(thread_events_key, 0, -1)
        
        if not event_keys:
            logger.info(f"No events found for thread {thread_id}")
            return []
        
        # Convert date strings to datetime objects for comparison
        start_dt = None
        end_dt = None
        
        if start_date:
            if isinstance(start_date, str):
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Invalid start date format: {start_date}")
            else:
                start_dt = start_date
        
        if end_date:
            if isinstance(end_date, str):
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Invalid end date format: {end_date}")
            else:
                end_dt = end_date
        
        # Fetch and filter events
        events = []
        for event_key in event_keys:
            try:
                # Get event data
                event_json = await redis.get(event_key)
                if not event_json:
                    continue
                
                event = json.loads(event_json)
                
                # Apply type filter if specified
                if event_type and event.get("event_type") != event_type:
                    continue
                
                # Parse event time for date filtering
                try:
                    event_time_str = event.get("event_time", "")
                    if not event_time_str:
                        continue
                    
                    event_dt = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
                    
                    # Apply date filters
                    if start_dt and event_dt < start_dt:
                        continue
                    if end_dt and event_dt > end_dt:
                        continue
                    
                    # Event passed all filters
                    events.append(event)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing event time '{event.get('event_time')}': {e}")
                    continue
                    
            except json.JSONDecodeError:
                logger.warning(f"Error decoding JSON for event key {event_key}")
                continue
            except Exception as e:
                logger.warning(f"Error processing event key {event_key}: {e}")
                continue
        
        # Sort events by time
        sorted_events = sorted(events, key=lambda x: x.get("event_time", ""))
        logger.info(f"Retrieved {len(sorted_events)} events for thread {thread_id}")
        return sorted_events
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return []

async def get_latest_event(thread_id: str, event_type: str) -> Optional[Dict[str, Any]]:
    """Get the latest event of a specific type for a thread with improved error handling."""
    try:
        # Get events filtered by type
        events = await get_events(thread_id=thread_id, event_type=event_type)
        
        if not events:
            logger.info(f"No {event_type} events found for thread {thread_id}")
            return None
        
        # Find the latest event by time
        latest = max(events, key=lambda x: x.get("event_time", ""))
        logger.info(f"Found latest {event_type} event for thread {thread_id}: {latest.get('event_time')}")
        return latest
        
    except Exception as e:
        logger.error(f"Error getting latest event: {e}")
        return None

async def get_summary(thread_id: str, period: str = "day") -> Dict[str, Any]:
    """Get a summary of routine events for a thread with enhanced error handling."""
    try:
        # Calculate time range based on period
        now = datetime.utcnow()
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "Today"
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "This Week"
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_name = "This Month"
        else:
            # Default to last 24 hours if period is unknown
            start_date = now - timedelta(days=1)
            period_name = "Last 24 Hours"
        
        logger.info(f"Generating {period} summary for thread {thread_id} from {start_date.isoformat()} to {now.isoformat()}")
        
        # Get events for the period
        events = await get_events(
            thread_id=thread_id,
            start_date=start_date,
            end_date=now
        )
        
        if not events:
            logger.info(f"No events found for thread {thread_id} in the {period} period")
            return {
                "period": period,
                "period_name": period_name,
                "start_date": start_date.isoformat(),
                "end_date": now.isoformat(),
                "routines": {}
            }
        
        # Process sleep events
        sleep_events = [e for e in events if e.get("event_type") == "sleep"]
        sleep_end_events = [e for e in events if e.get("event_type") == "sleep_end"]
        
        logger.info(f"Found {len(sleep_events)} sleep start events and {len(sleep_end_events)} sleep end events")
        
        total_sleep_duration = 0
        sleep_periods = []
        
        for sleep_event in sleep_events:
            try:
                sleep_start = datetime.fromisoformat(sleep_event.get("event_time", "").replace("Z", "+00:00"))
                
                # Find matching end event
                matching_end = next(
                    (e for e in sleep_end_events if 
                     datetime.fromisoformat(e.get("event_time", "").replace("Z", "+00:00")) > sleep_start),
                    None
                )
                
                if matching_end:
                    sleep_end = datetime.fromisoformat(matching_end.get("event_time", "").replace("Z", "+00:00"))
                    duration_minutes = int((sleep_end - sleep_start).total_seconds() / 60)  # Duration in minutes
                    duration_hours = duration_minutes / 60  # Convert to hours
                    total_sleep_duration += duration_hours
                    
                    sleep_periods.append({
                        "start": sleep_event.get("event_time"),
                        "end": matching_end.get("event_time"),
                        "duration": duration_hours
                    })
                    logger.info(f"Matched sleep period: {sleep_start} to {sleep_end}, duration: {duration_hours} hours")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error processing sleep event: {e}")
                continue
        
        # Process feed events
        feed_events = [e for e in events if e.get("event_type") == "feed" or e.get("event_type") == "feeding"]
        
        logger.info(f"Found {len(feed_events)} feeding events")
        
        # Calculate averages
        avg_sleep_duration = total_sleep_duration / len(sleep_periods) if sleep_periods else 0
        
        # Get latest events
        latest_sleep = sleep_periods[-1] if sleep_periods else None
        latest_feed = feed_events[-1] if feed_events else None
        
        # Construct summary
        summary = {
            "period": period,
            "period_name": period_name,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "routines": {
                "sleep": {
                    "total_events": len(sleep_periods),
                    "total_duration": round(total_sleep_duration, 2),
                    "average_duration": round(avg_sleep_duration, 2),
                    "latest_event": latest_sleep,
                    "events": sleep_periods
                },
                "feeding": {
                    "total_events": len(feed_events),
                    "latest_event": latest_feed,
                    "events": feed_events
                }
            }
        }
        
        logger.info(f"Generated summary for thread {thread_id} with {len(sleep_periods)} sleep periods and {len(feed_events)} feedings")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "period": period,
            "error": str(e),
            "routines": {}
        } 