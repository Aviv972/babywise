"""
Babywise Chatbot - Routine Tracker Database

This module implements the database operations for the Baby Routine Tracker feature,
allowing parents to log and retrieve routine events such as sleep and feeding.
"""

import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from backend.services.redis_service import (
    cache_routine_summary,
    get_cached_routine_summary,
    cache_recent_events,
    get_cached_recent_events,
    cache_active_routine,
    get_active_routine,
    invalidate_routine_cache,
    get_redis,
    RedisKeyPrefix
)
from backend.services.analytics_service import (
    update_daily_stats,
    update_weekly_stats,
    update_pattern_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if we're in Vercel environment (read-only filesystem)
IS_VERCEL = os.environ.get('VERCEL', '0') == '1' or os.path.exists('/.vercel')
logger.info(f"Running in Vercel environment: {IS_VERCEL}")

# Database file path for local development
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "routine_tracker.db")

# Ensure data directory exists if we're not in Vercel
if not IS_VERCEL:
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create data directory: {e}. Switching to Redis-only mode.")
        IS_VERCEL = True

def check_db_connection() -> bool:
    """Check if database connection is working"""
    if IS_VERCEL:
        # In Vercel, we'll use Redis so return True if Redis is working
        try:
            import asyncio
            result = asyncio.run(test_redis_connection())
            return result
        except Exception as e:
            logger.error(f"Redis connection check failed: {str(e)}")
            return False
    else:
        # In local development, use SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None and result[0] == 1
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

async def test_redis_connection() -> bool:
    """Test Redis connection"""
    try:
        redis = await get_redis()
        if redis is None:
            return False
        await redis.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False

def init_db():
    """Initialize the database with the required tables"""
    if IS_VERCEL:
        logger.info("Using Redis for storage in Vercel environment. No database initialization needed.")
        return True

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS routine_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create index on thread_id for faster queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_thread_id ON routine_events(thread_id)
        ''')
        
        # Create index on start_time for faster date range queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_start_time ON routine_events(start_time)
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def add_event(thread_id: str, event_type: str, start_time: datetime, 
                   end_time: Optional[datetime] = None, notes: Optional[str] = None) -> int:
    """
    Add a new routine event to the database or Redis
    
    Args:
        thread_id: Unique identifier for the conversation thread
        event_type: Type of event (sleep, feed)
        start_time: When the event started
        end_time: When the event ended (optional)
        notes: Additional notes about the event (optional)
        
    Returns:
        ID of the newly created event
    """
    # Normalize datetime objects to remove timezone info for consistent storage
    def normalize_datetime(dt):
        if dt is None:
            return None
        # If datetime has timezone info, convert to UTC and remove timezone
        if dt.tzinfo is not None:
            from datetime import timezone
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    
    # Normalize datetimes
    start_time_normalized = normalize_datetime(start_time)
    end_time_normalized = normalize_datetime(end_time)
    
    # Ensure start_time and end_time are in ISO format
    start_time_iso = start_time_normalized.isoformat()
    end_time_iso = end_time_normalized.isoformat() if end_time_normalized else None
    
    logger.info(f"Adding {event_type} event for thread {thread_id}")
    logger.info(f"Start time: {start_time_iso}, End time: {end_time_iso}, Notes: {notes}")
    
    if IS_VERCEL:
        # Use Redis in Vercel environment
        try:
            redis = await get_redis()
            if redis is None:
                logger.error("Failed to get Redis connection")
                raise Exception("Redis connection failed")
                
            # Create event object
            import uuid
            event_id = str(uuid.uuid4())
            event = {
                "id": event_id,
                "thread_id": thread_id,
                "event_type": event_type,
                "start_time": start_time_iso,
                "end_time": end_time_iso,
                "notes": notes,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Generate key for the event
            event_key = f"{RedisKeyPrefix.EVENT}:{thread_id}:{event_type}:{event_id}"
            
            # Store event in Redis
            await redis.set(event_key, json.dumps(event))
            
            # Add to thread's event list
            thread_events_key = f"{RedisKeyPrefix.THREAD_EVENTS}:{thread_id}"
            await redis.rpush(thread_events_key, event_key)
            
            logger.info(f"Added {event_type} event to Redis for thread {thread_id}: ID={event_id}")
            
            # Invalidate cache
            await invalidate_routine_cache(thread_id, event_type)
            
            return event_id
        except Exception as e:
            logger.error(f"Error adding event to Redis: {str(e)}", exc_info=True)
            raise
    else:
        # Use SQLite in local development
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Insert the event
            logger.info(f"Executing SQL INSERT with values: ({thread_id}, {event_type}, {start_time_iso}, {end_time_iso}, {notes})")
            cursor.execute('''
            INSERT INTO routine_events (thread_id, event_type, start_time, end_time, notes)
            VALUES (?, ?, ?, ?, ?)
            ''', (thread_id, event_type, start_time_iso, end_time_iso, notes))
            
            # Get the ID of the newly inserted event
            event_id = cursor.lastrowid
            
            conn.commit()
            logger.info(f"Added {event_type} event for thread {thread_id}: ID={event_id}, start={start_time_iso}, end={end_time_iso}")
            
            # Invalidate cache for this routine type
            await invalidate_routine_cache(thread_id, event_type)
            
            return event_id
        except Exception as e:
            logger.error(f"Error adding event to SQLite: {str(e)}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

async def update_event(event_id: int, end_time: Optional[datetime] = None, 
                      notes: Optional[str] = None) -> bool:
    """
    Update an existing routine event
    
    Args:
        event_id: ID of the event to update
        end_time: New end time for the event (optional)
        notes: New notes for the event (optional)
        
    Returns:
        True if the update was successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, get the event to know which cache to invalidate
        cursor.execute("SELECT thread_id, event_type FROM routine_events WHERE id = ?", (event_id,))
        result = cursor.fetchone()
        if not result:
            logger.warning(f"Event {event_id} not found")
            return False
            
        thread_id, event_type = result
        
        # Normalize datetime objects to remove timezone info for consistent storage
        def normalize_datetime(dt):
            if dt is None:
                return None
            # If datetime has timezone info, convert to UTC and remove timezone
            if dt.tzinfo is not None:
                from datetime import timezone
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        
        # Build the update query dynamically based on provided parameters
        update_parts = []
        params = []
        
        if end_time is not None:
            update_parts.append("end_time = ?")
            end_time_normalized = normalize_datetime(end_time)
            params.append(end_time_normalized.isoformat())
            
        if notes is not None:
            update_parts.append("notes = ?")
            params.append(notes)
            
        if not update_parts:
            logger.warning("No update parameters provided")
            return False
            
        query = f"UPDATE routine_events SET {', '.join(update_parts)} WHERE id = ?"
        params.append(event_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Updated event {event_id}")
            # Invalidate cache for this routine type
            await invalidate_routine_cache(thread_id, event_type)
            return True
        else:
            logger.warning(f"Event {event_id} not found or no changes made")
            return False
    except Exception as e:
        logger.error(f"Error updating event: {str(e)}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

async def get_events_by_date_range(thread_id: str, start_date: datetime, 
                                  end_date: datetime, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve events for a specific thread within a date range
    
    Args:
        thread_id: The conversation thread ID
        start_date: Start of the date range
        end_date: End of the date range
        event_type: Filter by event type (optional)
        
    Returns:
        List of events as dictionaries
    """
    conn = None
    try:
        # Log the input parameters
        logger.info(f"Getting events for thread {thread_id} from {start_date} to {end_date}, type: {event_type}")
        
        # Try to get from cache first
        if event_type:
            cached_events = await get_cached_recent_events(thread_id, event_type)
            if cached_events:
                logger.info(f"Retrieved {event_type} events from cache for thread {thread_id}")
                # Convert ISO strings back to datetime objects
                for event in cached_events:
                    if event.get('start_time'):
                        event['start_time'] = datetime.fromisoformat(event['start_time'])
                    if event.get('end_time'):
                        event['end_time'] = datetime.fromisoformat(event['end_time'])
                return cached_events
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables dictionary-like access to rows
        cursor = conn.cursor()
        
        # Normalize datetime objects to remove timezone info for consistent storage
        def normalize_datetime(dt):
            if dt is None:
                return None
            # If datetime has timezone info, convert to UTC and remove timezone
            if dt.tzinfo is not None:
                from datetime import timezone
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        
        # Normalize datetimes
        start_date_normalized = normalize_datetime(start_date)
        end_date_normalized = normalize_datetime(end_date)
        
        # Convert to ISO format for SQLite
        start_date_iso = start_date_normalized.isoformat()
        end_date_iso = end_date_normalized.isoformat()
        
        # Modified query to handle sleep events differently
        if event_type == 'sleep':
            # For sleep events, we want to get both sleep starts and their corresponding end events
            query = '''
            WITH sleep_events AS (
                SELECT 
                    e1.id,
                    e1.thread_id,
                    e1.event_type,
                    e1.start_time,
                    MIN(e2.start_time) as end_time,
                    e1.notes
                FROM routine_events e1
                LEFT JOIN routine_events e2 ON 
                    e2.thread_id = e1.thread_id AND
                    e2.event_type = 'sleep_end' AND
                    e2.start_time > e1.start_time
                WHERE e1.thread_id = ? AND
                    e1.event_type = 'sleep' AND
                    e1.start_time >= ? AND
                    e1.start_time <= ?
                GROUP BY e1.id
            )
            SELECT * FROM sleep_events
            ORDER BY start_time ASC
            '''
            params = [thread_id, start_date_iso, end_date_iso]
        else:
            # For other event types, use the original query
            query = '''
            SELECT * FROM routine_events 
            WHERE thread_id = ? AND 
            (
                (start_time >= ? AND start_time <= ?) OR  -- Events that start within the range
                (end_time >= ? AND end_time <= ?) OR      -- Events that end within the range
                (start_time <= ? AND (end_time >= ? OR end_time IS NULL))  -- Events that span the range
            )
            '''
            params = [thread_id, start_date_iso, end_date_iso, start_date_iso, end_date_iso, start_date_iso, start_date_iso]
        
        if event_type and event_type != 'sleep':
            query += ' AND event_type = ?'
            params.append(event_type)
            
        query += ' ORDER BY start_time ASC'
        
        logger.info(f"Retrieving events for thread {thread_id} from {start_date_iso} to {end_date_iso}")
        logger.info(f"Executing query: {query} with params: {params}")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to list of dictionaries
        events = []
        for row in rows:
            event_dict = dict(row)
            # Convert ISO strings back to datetime objects
            if event_dict.get('start_time'):
                event_dict['start_time'] = datetime.fromisoformat(event_dict['start_time'])
            if event_dict.get('end_time') and event_dict['end_time']:
                event_dict['end_time'] = datetime.fromisoformat(event_dict['end_time'])
            events.append(event_dict)
        
        logger.info(f"Retrieved {len(events)} events for thread {thread_id}")
        for idx, event in enumerate(events):
            logger.info(f"Event {idx+1}: {event}")
        
        # Cache events if event_type is provided
        if event_type:
            # Convert datetime objects to ISO strings for caching
            cache_events = []
            for event in events:
                cache_event = event.copy()
                if isinstance(cache_event.get('start_time'), datetime):
                    cache_event['start_time'] = cache_event['start_time'].isoformat()
                if isinstance(cache_event.get('end_time'), datetime):
                    cache_event['end_time'] = cache_event['end_time'].isoformat()
                cache_events.append(cache_event)
                
            await cache_recent_events(thread_id, event_type, cache_events)
            
        return events
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

async def get_routine_summary(thread_id: str, routine_type: str) -> Optional[Dict[str, Any]]:
    """
    Generate a summary of routine events for a specific thread
    
    Args:
        thread_id: The conversation thread ID
        routine_type: Type of routine (sleep, feeding, diaper)
        
    Returns:
        Summary dictionary or None if error
    """
    try:
        # Try to get from cache first
        cached_summary = await get_cached_routine_summary(thread_id, routine_type)
        if cached_summary:
            logger.info(f"Retrieved {routine_type} summary from cache for thread {thread_id}")
            return cached_summary
            
        # Get events from the last 24 hours
        end_date = datetime.utcnow()
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)  # Start of today
        
        events = await get_events_by_date_range(thread_id, start_date, end_date, routine_type)
        if not events:
            logger.info(f"No {routine_type} events found for thread {thread_id}")
            return None
            
        # Generate summary based on routine type
        summary = {
            "thread_id": thread_id,
            "routine_type": routine_type,
            "total_events": len(events),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "latest_event": None,
            "stats": {}
        }
        
        if events:
            latest_event = events[-1]
            summary["latest_event"] = {
                "id": latest_event["id"],
                "start_time": latest_event["start_time"].isoformat(),
                "end_time": latest_event["end_time"].isoformat() if latest_event["end_time"] else None,
                "notes": latest_event["notes"]
            }
            
            # Calculate routine-specific stats
            if routine_type == "sleep":
                total_sleep = timedelta()
                completed_events = 0
                
                # Group sleep events with their end events
                sleep_periods = []
                current_sleep = None
                
                for event in sorted(events, key=lambda x: x["start_time"]):
                    if not current_sleep:
                        current_sleep = event
                    elif event["end_time"]:
                        # This is an end event, calculate duration
                        duration = event["end_time"] - current_sleep["start_time"]
                        if duration.total_seconds() > 0:  # Only count positive durations
                            sleep_periods.append({
                                "start": current_sleep["start_time"],
                                "end": event["end_time"],
                                "duration": duration
                            })
                            total_sleep += duration
                            completed_events += 1
                        current_sleep = None
                
                # Calculate stats
                summary["stats"].update({
                    "total_sleep_hours": round(total_sleep.total_seconds() / 3600, 2),
                    "average_sleep_hours": round((total_sleep.total_seconds() / 3600) / completed_events if completed_events > 0 else 0, 2),
                    "completed_events": completed_events,
                    "sleep_periods": [{
                        "start": period["start"].isoformat(),
                        "end": period["end"].isoformat(),
                        "duration_hours": round(period["duration"].total_seconds() / 3600, 2)
                    } for period in sleep_periods]
                })
                
            elif routine_type == "feeding":
                total_feeds = len(events)
                feed_times = [event["start_time"] for event in events]
                
                # Calculate average time between feeds
                if len(feed_times) > 1:
                    time_diffs = []
                    for i in range(1, len(feed_times)):
                        diff = feed_times[i] - feed_times[i-1]
                        time_diffs.append(diff.total_seconds() / 3600)  # Convert to hours
                    avg_time_between = sum(time_diffs) / len(time_diffs)
                else:
                    avg_time_between = 0
                
                summary["stats"].update({
                    "total_feeds": total_feeds,
                    "feeds_per_day": total_feeds,
                    "average_time_between_feeds": round(avg_time_between, 2)
                })
        
        # Cache the summary
        await cache_routine_summary(thread_id, routine_type, summary)
        logger.info(f"Generated and cached {routine_type} summary for thread {thread_id}")
        
        return summary
    except Exception as e:
        logger.error(f"Error generating routine summary: {str(e)}", exc_info=True)
        return None

async def get_latest_event(thread_id: str, event_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest event of a specific type for a thread
    
    Args:
        thread_id: The thread ID to get the latest event for
        event_type: The type of event to retrieve
        
    Returns:
        The latest event as a dictionary, or None if no events found
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, thread_id, event_type, start_time, end_time, notes, created_at
        FROM routine_events
        WHERE thread_id = ? AND event_type = ?
        ORDER BY start_time DESC
        LIMIT 1
        ''', (thread_id, event_type))
        
        result = cursor.fetchone()
        
        if result:
            return {
                "id": result[0],
                "thread_id": result[1],
                "event_type": result[2],
                "start_time": result[3],
                "end_time": result[4],
                "notes": result[5],
                "created_at": result[6]
            }
        return None
        
    except Exception as e:
        logger.error(f"Error getting latest event: {str(e)}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

async def delete_event(event_id: int) -> bool:
    """
    Delete a routine event by ID
    
    Args:
        event_id: The ID of the event to delete
        
    Returns:
        True if the event was deleted successfully, False otherwise
    """
    try:
        # Get event details first for cache invalidation
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT thread_id, event_type FROM routine_events WHERE id = ?",
            (event_id,)
        )
        
        event = cursor.fetchone()
        if not event:
            logger.warning(f"Event with ID {event_id} not found")
            return False
            
        thread_id = event['thread_id']
        event_type = event['event_type']
        
        # Delete the event
        cursor.execute(
            "DELETE FROM routine_events WHERE id = ?",
            (event_id,)
        )
        
        conn.commit()
        conn.close()
        
        # Invalidate cache
        await invalidate_routine_cache(thread_id, event_type)
        
        # Update analytics
        await update_daily_stats(thread_id, event_type)
        await update_weekly_stats(thread_id, event_type)
        await update_pattern_stats(thread_id, event_type)
        
        logger.info(f"Deleted event {event_id} successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {str(e)}")
        return False

async def generate_summary(thread_id: str, routine_type: str = None, period: str = "day") -> Dict[str, Any]:
    """
    Generate a summary of routine events for a specific period
    
    Args:
        thread_id: The thread ID to generate summary for
        routine_type: The type of routine to summarize (None for all types)
        period: The period to summarize ('day', 'week', or 'month')
        
    Returns:
        A dictionary containing the summary data
    """
    try:
        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=1)  # Default to day
            
        logger.info(f"Generating summary for thread {thread_id} from {start_date.isoformat()} to {end_date.isoformat()}")
        
        # Get events for the period
        events = await get_events_by_date_range(thread_id, start_date, end_date, routine_type)
        logger.info(f"Retrieved {len(events)} events for thread {thread_id}")
        
        # Log all events for debugging
        for i, event in enumerate(events):
            logger.info(f"Event {i+1}: id={event.get('id')}, type={event.get('event_type')}, "
                       f"start={event.get('start_time')}, end={event.get('end_time')}, "
                       f"notes={event.get('notes')}")
        
        # Initialize summary
        summary = {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_events": len(events),
            "routines": {}
        }
        
        # Group events by type
        event_types = {}
        for event in events:
            event_type = event["event_type"]
            if event_type not in event_types:
                event_types[event_type] = []
            event_types[event_type].append(event)
            
        logger.info(f"Event types found: {list(event_types.keys())}")
        
        # Generate stats for each event type
        for event_type, type_events in event_types.items():
            logger.info(f"Processing {len(type_events)} events of type {event_type}")
            
            type_summary = {
                "total_events": len(type_events),
                "total_duration": 0,
                "average_duration": 0,
                "latest_event": None
            }
            
            total_duration = timedelta()
            completed_events = 0
            
            # First, sort events by start time
            type_events.sort(key=lambda x: x["start_time"])
            
            # Process each event
            for event in type_events:
                logger.info(f"Processing event {event.get('id')} of type {event_type}")
                
                # Skip events with missing start time
                if not event["start_time"]:
                    logger.info(f"Skipping event {event['id']} because it has no start_time")
                    continue
                
                # Handle start_time
                if isinstance(event["start_time"], str):
                    start_time = datetime.fromisoformat(event["start_time"])
                    logger.info(f"Converted start_time string to datetime: {start_time}")
                else:
                    start_time = event["start_time"]
                    logger.info(f"Using start_time as datetime: {start_time}")
                
                # For events with no end_time, use the next event's start_time or current time
                if not event["end_time"]:
                    logger.info(f"Event {event['id']} has no end_time, using next event start or current time")
                    
                    # Find the next event of the same type
                    next_event = None
                    for next_evt in type_events:
                        if next_evt["id"] > event["id"] and next_evt["start_time"] > start_time:
                            next_event = next_evt
                            break
                    
                    if next_event:
                        # Use the next event's start time as this event's end time
                        if isinstance(next_event["start_time"], str):
                            end_time = datetime.fromisoformat(next_event["start_time"])
                        else:
                            end_time = next_event["start_time"]
                        logger.info(f"Using next event's start time as end time: {end_time}")
                    else:
                        # Use current time as end time
                        end_time = datetime.utcnow()
                        logger.info(f"Using current time as end time: {end_time}")
                else:
                    # Handle end_time
                    if isinstance(event["end_time"], str):
                        end_time = datetime.fromisoformat(event["end_time"])
                        logger.info(f"Converted end_time string to datetime: {end_time}")
                    else:
                        end_time = event["end_time"]
                        logger.info(f"Using end_time as datetime: {end_time}")
                
                # Handle cases where end_time equals start_time
                if end_time == start_time:
                    # Use a minimum duration of 1 minute
                    logger.info(f"Event {event['id']} has equal start and end times, using minimum duration of 1 minute")
                    duration = timedelta(minutes=1)
                elif end_time > start_time:
                    duration = end_time - start_time
                    logger.info(f"Event {event['id']} has duration: {duration} ({duration.total_seconds()/60:.1f} minutes)")
                else:
                    logger.info(f"Skipping event {event['id']} because end_time {end_time} is before start_time {start_time}")
                    continue
                
                # Add to total duration
                total_duration += duration
                completed_events += 1
                logger.info(f"Event {event['id']} has duration: {duration} ({duration.total_seconds()/60:.1f} minutes)")
                logger.info(f"Running total duration: {total_duration} ({total_duration.total_seconds()/60:.1f} minutes)")
                    
            if completed_events > 0:
                type_summary["total_duration"] = total_duration.total_seconds() / 3600  # Convert to hours
                type_summary["average_duration"] = type_summary["total_duration"] / completed_events
                logger.info(f"Total duration: {type_summary['total_duration']} hours ({total_duration.total_seconds()/60:.1f} minutes)")
                logger.info(f"Average duration: {type_summary['average_duration']} hours ({type_summary['average_duration']*60:.1f} minutes)")
            else:
                logger.info("No completed events with valid durations found")
            
            # Add latest event
            if type_events:
                latest = type_events[-1]
                type_summary["latest_event"] = {
                    "id": latest["id"],
                    "start_time": latest["start_time"],
                    "end_time": latest["end_time"],
                    "notes": latest["notes"]
                }
                logger.info(f"Latest event: id={latest['id']}, start={latest['start_time']}, end={latest['end_time']}")
                
            summary["routines"][event_type] = type_summary
            
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "period": period,
            "total_events": 0,
            "routines": {}
        }

# Initialize the database when the module is imported
init_db() 