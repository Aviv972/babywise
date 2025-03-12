#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database module for handling routine events
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from backend.services.redis_service import (
    redis_connection, RedisKeyPrefix, get_with_fallback, set_with_fallback, 
    delete_with_fallback, add_event_to_thread, list_append
)

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
        # Validate inputs
        if not thread_id:
            logger.error("Cannot add event with empty thread_id")
            raise ValueError("thread_id is required")
            
        if not event_type:
            logger.error("Cannot add event with empty event_type")
            raise ValueError("event_type is required")
            
        # Handle None or empty event_time
        if not event_time:
            logger.warning(f"Event time is empty or None, using current UTC time")
            event_time = datetime.utcnow().isoformat()
        
        # Create event object
        event = {
            "thread_id": thread_id,
            "event_type": event_type,
            "event_time": event_time,
            "event_data": event_data or {},
            "local_id": local_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Generate event ID and key - ensure strings and handle special chars safely
        safe_event_time = str(event_time).replace(':', '-').replace('.', '-').replace(' ', 'T')
        event_id = f"{safe_event_time}-{local_id or event_type}"
        event_key = f"{RedisKeyPrefix.EVENT}:{thread_id}:{event_type}:{event_id}"
        
        # Store event in Redis
        event_json = json.dumps(event)
        store_success = await set_with_fallback(event_key, event_json)
        
        if not store_success:
            logger.error(f"Failed to store event for thread {thread_id}")
            raise Exception("Failed to store event")
            
        # Add to thread's event list
        list_success = await add_event_to_thread(thread_id, event_key)
        
        if not list_success:
            logger.warning(f"Failed to add event to thread list for {thread_id}")
            # Continue since the event is still stored
            
        logger.info(f"Successfully added {event_type} event for thread {thread_id}")
        return event
        
    except Exception as e:
        logger.error(f"Error adding event: {e}")
        # Return a partial event with error info for better debugging
        return {
            "thread_id": thread_id,
            "event_type": event_type,
            "event_time": event_time if event_time else datetime.utcnow().isoformat(),
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
    
    # Convert date strings to datetime objects for comparison
    start_dt = None
    end_dt = None
    
    if start_date:
        if isinstance(start_date, str):
            try:
                # Parse the string to a timezone-aware datetime
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                # Convert to naive datetime in UTC for consistent comparison
                start_dt = start_dt.replace(tzinfo=None)
                logger.info(f"Converted start_date string to naive datetime: {start_dt}")
            except ValueError:
                logger.warning(f"Invalid start date format: {start_date}")
        else:
            # If it's already a datetime, ensure it's timezone-naive
            if start_date.tzinfo is not None:
                # Convert to UTC then remove timezone
                from datetime import timezone
                start_dt = start_date.astimezone(timezone.utc).replace(tzinfo=None)
                logger.info(f"Converted timezone-aware start_date to naive: {start_dt}")
            else:
                start_dt = start_date
                logger.info(f"Using naive start_date as is: {start_dt}")
    
    if end_date:
        if isinstance(end_date, str):
            try:
                # Parse the string to a timezone-aware datetime
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                # Convert to naive datetime in UTC for consistent comparison
                end_dt = end_dt.replace(tzinfo=None)
                logger.info(f"Converted end_date string to naive datetime: {end_dt}")
            except ValueError:
                logger.warning(f"Invalid end date format: {end_date}")
        else:
            # If it's already a datetime, ensure it's timezone-naive
            if end_date.tzinfo is not None:
                # Convert to UTC then remove timezone
                from datetime import timezone
                end_dt = end_date.astimezone(timezone.utc).replace(tzinfo=None)
                logger.info(f"Converted timezone-aware end_date to naive: {end_dt}")
            else:
                end_dt = end_date
                logger.info(f"Using naive end_date as is: {end_dt}")
    
    events = []
    try:
        async with redis_connection() as client:
            if not client:
                logger.error("Failed to get Redis connection for retrieving events")
                return []
            
            # Get the thread's event keys
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            event_keys = await client.lrange(thread_events_key, 0, -1)
            
            if not event_keys:
                logger.info(f"No events found for thread {thread_id}")
                return []
            
            # Use pipeline for efficient batch retrieval
            pipe = client.pipeline()
            for key in event_keys:
                pipe.get(key)
            
            results = await pipe.execute()
            
            # Process and filter events
            for i, event_json in enumerate(results):
                if not event_json:
                    continue
                
                try:
                    # First we need to check if our event_json is already an object or a JSON string
                    if isinstance(event_json, str):
                        try:
                            event = json.loads(event_json)
                        except json.JSONDecodeError:
                            # If the event_json is just a key (not the actual content), we need to fetch the actual data
                            logger.warning(f"Event key retrieval issue - got a key instead of data: {event_json}")
                            actual_event_data = await client.get(event_json)
                            if actual_event_data:
                                try:
                                    event = json.loads(actual_event_data)
                                except json.JSONDecodeError:
                                    logger.warning(f"Error decoding JSON from key: {event_json}")
                                    continue
                            else:
                                logger.warning(f"No data found for event key: {event_json}")
                                continue
                    else:
                        # If it's already an object (deserialized JSON), use it directly
                        event = event_json
                    
                    # Apply type filter if specified
                    if event_type and event.get("event_type") != event_type:
                        continue
                    
                    # Parse event time for date filtering
                    try:
                        event_time_str = event.get("event_time", "")
                        if not event_time_str:
                            logger.warning(f"Event missing event_time: {event}")
                            continue
                        
                        logger.info(f"Processing event of type {event.get('event_type')} with time: {event_time_str}")
                        
                        # Handle potential None values or format issues
                        try:
                            # First try direct parsing of ISO format with timezone handling
                            if event_time_str.endswith('Z'):
                                logger.info(f"Converting Z timezone format to +00:00 for event time: {event_time_str}")
                                event_time_str = event_time_str.replace("Z", "+00:00")
                                
                            # Parse to timezone-aware datetime, then convert to naive in UTC for comparison
                            event_dt = datetime.fromisoformat(event_time_str)
                            
                            # If it has timezone info, convert to UTC and remove timezone
                            if event_dt.tzinfo is not None:
                                from datetime import timezone
                                old_dt = event_dt
                                event_dt = event_dt.astimezone(timezone.utc).replace(tzinfo=None)
                                logger.info(f"Converted timezone-aware datetime {old_dt} to UTC naive datetime: {event_dt}")
                            else:
                                logger.info(f"Event time is already a naive datetime: {event_dt}")
                                
                        except (AttributeError, ValueError) as e:
                            # If that fails, try to handle common format issues
                            logger.warning(f"Failed to parse event time '{event_time_str}' with fromisoformat: {e}")
                            
                            # Try fallback approaches
                            try:
                                # If it's None or not a string
                                if event_time_str is None:
                                    logger.error("Event time is None, skipping event")
                                    continue
                                    
                                # Try different formats
                                if 'T' in event_time_str:
                                    event_dt = datetime.strptime(event_time_str, "%Y-%m-%dT%H:%M:%S.%f")
                                    logger.info(f"Parsed with ISO format without timezone: {event_dt}")
                                else:
                                    event_dt = datetime.strptime(event_time_str, "%Y-%m-%d %H:%M:%S.%f")
                                    logger.info(f"Parsed with standard datetime format: {event_dt}")
                                # These are already naive datetimes, no need to modify
                            except (ValueError, TypeError) as e:
                                logger.error(f"Could not parse event time '{event_time_str}' with standard formats: {e}")
                                
                                # One last attempt with common formats
                                try:
                                    if 'T' in event_time_str:
                                        # Try without milliseconds
                                        event_dt = datetime.strptime(event_time_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                        logger.info(f"Parsed with ISO format without milliseconds: {event_dt}")
                                    else:
                                        # Try without milliseconds
                                        event_dt = datetime.strptime(event_time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                                        logger.info(f"Parsed with standard format without milliseconds: {event_dt}")
                                except (ValueError, TypeError, IndexError):
                                    # Last resort - skip this event
                                    logger.error(f"All parsing attempts failed for event time '{event_time_str}', skipping event")
                                    continue
                        
                        # Log filter checks
                        if start_dt:
                            logger.info(f"Checking if event time {event_dt} is after start date {start_dt}")
                            
                        if end_dt:
                            logger.info(f"Checking if event time {event_dt} is before end date {end_dt}")
                            
                        # Apply date filters
                        if start_dt and event_dt < start_dt:
                            logger.info(f"Event time {event_dt} is before start date {start_dt}, skipping")
                            continue
                            
                        if end_dt and event_dt > end_dt:
                            logger.info(f"Event time {event_dt} is after end date {end_dt}, skipping")
                            continue
                        
                        # Event passed all filters
                        logger.info(f"Event passed all filters: {event.get('event_type')} at {event_dt}")
                        events.append(event)
                        
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing event time '{event.get('event_time')}': {e}")
                        continue
                        
                except json.JSONDecodeError:
                    logger.warning(f"Error decoding JSON for event key {event_keys[i]}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing event key {event_keys[i]}: {e}")
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
        logger.info(f"Current server time (UTC): {now.isoformat()}")
        
        # Try to get cached summary first
        cache_key = f"{RedisKeyPrefix.ROUTINE_SUMMARY}:{thread_id}:{period}"
        cached_summary = await get_with_fallback(cache_key)
        
        if cached_summary:
            logger.info(f"Using cached summary for thread {thread_id}, period {period}")
            return cached_summary
        
        # Get events for the period
        logger.info(f"Retrieving events for thread {thread_id} from {start_date.isoformat()} to {now.isoformat()}")
        events = await get_events(
            thread_id=thread_id,
            start_date=start_date,
            end_date=now
        )
        
        # Log the raw events retrieved for debugging
        logger.info(f"Retrieved {len(events)} total events for summary generation")
        for i, event in enumerate(events):
            logger.info(f"Raw event {i+1}: type={event.get('event_type')}, time={event.get('event_time')}, id={event.get('local_id')}")
            
        if not events:
            logger.warning(f"No events found for thread {thread_id} in the {period} period")
            empty_summary = {
                "period": period,
                "period_name": period_name,
                "start_date": start_date.isoformat(),
                "end_date": now.isoformat(),
                "thread_id": thread_id,
                "routines": {}
            }
            
            # Cache the empty summary briefly to avoid repeated processing
            await set_with_fallback(cache_key, empty_summary, 60)  # Cache for 1 minute to allow for retries
            return empty_summary
        
        # Force clear any existing cache to ensure fresh results
        await delete_with_fallback(cache_key)
        logger.info(f"Cleared existing summary cache for thread {thread_id}")
        
        # Process sleep events
        sleep_events = [e for e in events if e.get("event_type") == "sleep"]
        sleep_end_events = [e for e in events if e.get("event_type") == "sleep_end"]
        
        logger.info(f"Found {len(sleep_events)} sleep start events and {len(sleep_end_events)} sleep end events")
        
        # Debug log the events for troubleshooting
        for i, event in enumerate(sleep_events):
            logger.info(f"Sleep event {i+1}: time={event.get('event_time')}, id={event.get('local_id')}")
        
        for i, event in enumerate(sleep_end_events):
            logger.info(f"Sleep end event {i+1}: time={event.get('event_time')}, id={event.get('local_id')}")
        
        total_sleep_duration = 0
        sleep_periods = []
        
        # If we have sleep_end events but no sleep events, try to create sleep periods for them
        # Many parents only track wakeups but not sleep starts
        if len(sleep_end_events) > 0 and len(sleep_events) == 0:
            logger.info("Only found sleep end events, creating virtual sleep periods")
            
            # Sort sleep end events by time
            sorted_end_events = sorted(sleep_end_events, key=lambda x: x.get("event_time", ""))
            
            for end_event in sorted_end_events:
                try:
                    end_time = datetime.fromisoformat(end_event.get("event_time", "").replace("Z", "+00:00"))
                    
                    # Use a reasonable default sleep duration for infants (2 hours)
                    start_time = end_time - timedelta(hours=2)
                    
                    # If start time would be before our date range, adjust it
                    if start_time < start_date:
                        start_time = start_date
                    
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    
                    if duration_hours <= 0:
                        logger.warning(f"Calculated non-positive duration: {duration_hours} for sleep end event. Skipping.")
                        continue
                    
                    total_sleep_duration += duration_hours
                    
                    sleep_periods.append({
                        "start": start_time.isoformat(),
                        "end": end_event.get("event_time"),
                        "duration": round(duration_hours, 2),
                        "start_id": None,  # Virtual sleep start
                        "end_id": end_event.get("local_id"),
                        "is_virtual": True
                    })
                    
                    logger.info(f"Created virtual sleep period: {start_time} to {end_time}, duration: {duration_hours} hours")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error processing sleep end event: {e}")
                    continue
        
        # Track processed sleep end events to avoid duplicates
        processed_sleep_ends = set()
        
        # Match sleep events with sleep end events
        for sleep_event in sleep_events:
            try:
                sleep_event_time = sleep_event.get("event_time", "")
                logger.info(f"Processing sleep event with time: {sleep_event_time}")
                
                # Handle Z vs +00:00 timezone formats
                sleep_start = datetime.fromisoformat(sleep_event_time.replace("Z", "+00:00"))
                
                # Find matching end event
                matching_end = None
                closest_time_diff = timedelta(days=1)  # Start with a large value
                
                for end_event in sleep_end_events:
                    # Skip already processed end events
                    end_id = end_event.get("local_id")
                    if end_id in processed_sleep_ends:
                        logger.info(f"Skipping already processed end event with id: {end_id}")
                        continue
                    
                    end_time_str = end_event.get("event_time", "")
                    logger.info(f"Checking sleep end event with time: {end_time_str}")
                    
                    try:
                        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Error parsing end time '{end_time_str}': {e}")
                        continue
                        
                    # End time must be after start time
                    if end_time > sleep_start:
                        time_diff = end_time - sleep_start
                        
                        # If it's the closest end time so far, use it
                        if time_diff < closest_time_diff:
                            closest_time_diff = time_diff
                            matching_end = end_event
                
                if matching_end:
                    end_id = matching_end.get("local_id")
                    logger.info(f"Found matching end event with id: {end_id} and time: {matching_end.get('event_time')}")
                    
                    if end_id:  # Mark as processed if it has an ID
                        processed_sleep_ends.add(end_id)
                    
                    sleep_end = datetime.fromisoformat(matching_end.get("event_time", "").replace("Z", "+00:00"))
                    duration_minutes = int((sleep_end - sleep_start).total_seconds() / 60)  # Duration in minutes
                    duration_hours = duration_minutes / 60  # Convert to hours
                    
                    # Validate duration - skip unreasonable values
                    if duration_hours > 24:  # More than a day of sleep
                        logger.warning(f"Unreasonable sleep duration: {duration_hours} hours. Skipping.")
                        continue
                    
                    total_sleep_duration += duration_hours
                    
                    sleep_periods.append({
                        "start": sleep_event.get("event_time"),
                        "end": matching_end.get("event_time"),
                        "duration": round(duration_hours, 2),
                        "start_id": sleep_event.get("local_id"),
                        "end_id": matching_end.get("local_id")
                    })
                    logger.info(f"Matched sleep period: {sleep_start} to {sleep_end}, duration: {duration_hours} hours")
                else:
                    # If no matching end event, create a sleep period with estimated end time
                    # Assume baby is still sleeping if sleep event is recent (within 12 hours)
                    time_since_sleep = now - sleep_start
                    
                    if time_since_sleep.total_seconds() < 12 * 3600:  # 12 hours
                        logger.info(f"No end event found, but sleep start is recent. Creating open-ended sleep period.")
                        
                        # For ongoing sleep, use current time as temporary end
                        duration_hours = time_since_sleep.total_seconds() / 3600
                        
                        sleep_periods.append({
                            "start": sleep_event.get("event_time"),
                            "end": None,  # Ongoing sleep
                            "duration": round(duration_hours, 2),
                            "start_id": sleep_event.get("local_id"),
                            "end_id": None,
                            "is_ongoing": True
                        })
                        
                        # Add to total duration (ongoing sleep counts too)
                        total_sleep_duration += duration_hours
                        
                        logger.info(f"Created ongoing sleep period: {sleep_start} to (now), duration so far: {duration_hours} hours")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error processing sleep event: {e}")
                continue
        
        # Process unmatched sleep end events that might not have a corresponding start
        # This is valuable when parents only logged the wake-up time but not the sleep time
        for end_event in sleep_end_events:
            end_id = end_event.get("local_id")
            if end_id not in processed_sleep_ends:
                try:
                    logger.info(f"Processing unmatched sleep end event with id: {end_id}")
                    
                    end_time = datetime.fromisoformat(end_event.get("event_time", "").replace("Z", "+00:00"))
                    
                    # Assume a reasonable sleep duration (2 hours) before the end time
                    start_time = end_time - timedelta(hours=2)
                    
                    # If start time would be before our date range, adjust it
                    if start_time < start_date:
                        start_time = start_date
                    
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    
                    if duration_hours <= 0:
                        logger.warning(f"Calculated non-positive duration: {duration_hours} for sleep end event. Skipping.")
                        continue
                    
                    total_sleep_duration += duration_hours
                    
                    sleep_periods.append({
                        "start": start_time.isoformat(),
                        "end": end_event.get("event_time"),
                        "duration": round(duration_hours, 2),
                        "start_id": None,  # Virtual sleep start
                        "end_id": end_event.get("local_id"),
                        "is_virtual": True
                    })
                    
                    logger.info(f"Created virtual sleep period for unmatched end event: {start_time} to {end_time}, duration: {duration_hours} hours")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error processing unmatched sleep end event: {e}")
                    continue
        
        # Process feed events
        feed_events = [e for e in events if e.get("event_type") in ["feed", "feeding"]]
        
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
            "thread_id": thread_id,  # Adding thread_id for better traceability
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
        
        # Cache the summary
        await set_with_fallback(cache_key, summary, 300)  # Cache for 5 minutes
        
        logger.info(f"Generated summary for thread {thread_id} with {len(sleep_periods)} sleep periods and {len(feed_events)} feedings")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "period": period,
            "error": str(e),
            "thread_id": thread_id,
            "routines": {}
        } 