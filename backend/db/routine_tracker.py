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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file path
# Check if running on Vercel
if 'VERCEL' in os.environ:
    # Use /tmp directory for Vercel deployment
    DB_PATH = os.path.join('/tmp', "routine_tracker.db")
    logger.info(f"Running on Vercel, using database path: {DB_PATH}")
else:
    # Use regular path for local development
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "routine_tracker.db")
    logger.info(f"Running locally, using database path: {DB_PATH}")

# Ensure data directory exists
if 'VERCEL' not in os.environ:  # Only create directory locally
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Initialize the database with the required tables"""
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
        if conn:
            conn.close()

def add_event(thread_id: str, event_type: str, start_time: datetime, 
              end_time: Optional[datetime] = None, notes: Optional[str] = None) -> int:
    """
    Add a new routine event to the database
    
    Args:
        thread_id: Unique identifier for the conversation thread
        event_type: Type of event (sleep, feed)
        start_time: When the event started
        end_time: When the event ended (optional)
        notes: Additional notes about the event (optional)
        
    Returns:
        ID of the newly created event
    """
    conn = None
    try:
        logger.info(f"Adding {event_type} event for thread {thread_id}")
        logger.info(f"Start time: {start_time}, End time: {end_time}, Notes: {notes}")
        
        conn = sqlite3.connect(DB_PATH)
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
        start_time_normalized = normalize_datetime(start_time)
        end_time_normalized = normalize_datetime(end_time)
        
        # Ensure start_time and end_time are in ISO format
        start_time_iso = start_time_normalized.isoformat()
        end_time_iso = end_time_normalized.isoformat() if end_time_normalized else None
        
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
        return event_id
    except Exception as e:
        logger.error(f"Error adding event: {str(e)}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

def update_event(event_id: int, end_time: Optional[datetime] = None, 
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
        
        # Normalize datetime objects to remove timezone info for consistent storage
        def normalize_datetime(dt):
            if dt is None:
                return None
            # If datetime has timezone info, convert to UTC and remove timezone
            if dt.tzinfo is not None:
                from datetime import timezone
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        
        # If updating with end_time, check if we need to handle special cases
        if end_time is not None:
            # Get the current event to check its start_time
            cursor.execute("SELECT start_time FROM routine_events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            
            if row:
                try:
                    start_time_str = row[0]
                    start_time = datetime.fromisoformat(start_time_str.split('+')[0] if '+' in start_time_str else start_time_str)
                    end_time_normalized = normalize_datetime(end_time)
                    
                    # Check if end_time is before start_time
                    if end_time_normalized < start_time:
                        # Check if they're on different days
                        if end_time_normalized.date() < start_time.date():
                            # End time is from a previous day (data error)
                            logger.warning(f"End time is from a previous day for event {event_id}, adjusting to next day")
                            # Adjust to be on the next day after start_time
                            days_diff = (start_time.date() - end_time_normalized.date()).days
                            end_time_normalized = end_time_normalized + timedelta(days=days_diff + 1)
                        else:
                            # Same day but end_time is earlier than start_time
                            # Check if this looks like a typical overnight sleep pattern
                            is_likely_overnight = (start_time.hour >= 20 or start_time.hour <= 3) and (end_time_normalized.hour >= 5 and end_time_normalized.hour <= 10)
                            
                            if is_likely_overnight:
                                # Normal overnight sleep, add one day to end_time
                                logger.info(f"Treating as overnight sleep for event {event_id}")
                                end_time_normalized = end_time_normalized + timedelta(days=1)
                            else:
                                # For events entered out of order, we'll keep the times as is
                                # The summary generation will handle swapping them for duration calculation
                                logger.warning(f"End time before start time on same day for event {event_id}, likely entered out of order")
                        
                        # Update the end_time with our adjusted value
                        end_time = end_time_normalized
                except Exception as e:
                    logger.error(f"Error processing times for event {event_id}: {str(e)}")
        
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

def get_events_by_date_range(thread_id: str, start_date: datetime, 
                            end_date: datetime, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve events for a specific thread within a date range
    
    Args:
        thread_id: Unique identifier for the conversation thread
        start_date: Start of the date range
        end_date: End of the date range
        event_type: Filter by event type (optional)
        
    Returns:
        List of events as dictionaries
    """
    try:
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
        
        # Normalize input dates
        start_date_normalized = normalize_datetime(start_date)
        end_date_normalized = normalize_datetime(end_date)
        
        # Convert dates to ISO format for SQLite
        start_date_iso = start_date_normalized.isoformat()
        end_date_iso = end_date_normalized.isoformat()
        
        logger.info(f"Retrieving events for thread {thread_id} from {start_date_iso} to {end_date_iso}")
        
        query = '''
        SELECT * FROM routine_events 
        WHERE thread_id = ? AND start_time >= ? AND start_time <= ?
        '''
        params = [thread_id, start_date_iso, end_date_iso]
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
            
        query += " ORDER BY start_time ASC"
        
        logger.info(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        events = []
        for row in rows:
            event = dict(row)
            # Parse ISO format strings back to datetime objects
            if event['start_time']:
                try:
                    event['start_time'] = datetime.fromisoformat(event['start_time'])
                except ValueError:
                    # Handle timezone format issues
                    if '+' in event['start_time']:
                        clean_time = event['start_time'].split('+')[0]
                        event['start_time'] = datetime.fromisoformat(clean_time)
                    else:
                        event['start_time'] = datetime.fromisoformat(event['start_time'])
            
            if event['end_time']:
                try:
                    event['end_time'] = datetime.fromisoformat(event['end_time'])
                except ValueError:
                    # Handle timezone format issues
                    if '+' in event['end_time']:
                        clean_time = event['end_time'].split('+')[0]
                        event['end_time'] = datetime.fromisoformat(clean_time)
                    else:
                        event['end_time'] = datetime.fromisoformat(event['end_time'])
            
            if event['created_at']:
                try:
                    event['created_at'] = datetime.fromisoformat(event['created_at'])
                except ValueError:
                    # Handle timezone format issues
                    if '+' in event['created_at']:
                        clean_time = event['created_at'].split('+')[0]
                        event['created_at'] = datetime.fromisoformat(clean_time)
                    else:
                        event['created_at'] = datetime.fromisoformat(event['created_at'])
            
            events.append(event)
            
        logger.info(f"Retrieved {len(events)} events for thread {thread_id} in date range")
        for i, event in enumerate(events):
            logger.info(f"Event {i+1}: {event['event_type']} - start: {event['start_time']}, end: {event['end_time']}")
        
        return events
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

def delete_event(event_id: int) -> bool:
    """
    Delete a routine event
    
    Args:
        event_id: ID of the event to delete
        
    Returns:
        True if the deletion was successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM routine_events WHERE id = ?", (event_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Deleted event {event_id}")
            return True
        else:
            logger.warning(f"Event {event_id} not found")
            return False
    except Exception as e:
        logger.error(f"Error deleting event: {str(e)}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

def get_latest_event(thread_id: str, event_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent event of a specific type for a thread
    
    Args:
        thread_id: Unique identifier for the conversation thread
        event_type: Type of event to retrieve
        
    Returns:
        The most recent event as a dictionary, or None if no events found
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # First try to find an active event (one without an end_time)
        cursor.execute('''
        SELECT * FROM routine_events 
        WHERE thread_id = ? AND event_type = ? AND end_time IS NULL
        ORDER BY start_time DESC LIMIT 1
        ''', (thread_id, event_type))
        
        row = cursor.fetchone()
        
        # If no active event found, get the latest event regardless of end_time
        if not row:
            cursor.execute('''
            SELECT * FROM routine_events 
            WHERE thread_id = ? AND event_type = ?
            ORDER BY start_time DESC LIMIT 1
            ''', (thread_id, event_type))
            
            row = cursor.fetchone()
        
        if row:
            event = dict(row)
            # Parse ISO format strings back to datetime objects
            if event['start_time']:
                try:
                    event['start_time'] = datetime.fromisoformat(event['start_time'])
                except ValueError:
                    # Handle timezone format issues
                    if '+' in event['start_time']:
                        clean_time = event['start_time'].split('+')[0]
                        event['start_time'] = datetime.fromisoformat(clean_time)
                    else:
                        event['start_time'] = datetime.fromisoformat(event['start_time'])
            
            if event['end_time']:
                try:
                    event['end_time'] = datetime.fromisoformat(event['end_time'])
                except ValueError:
                    # Handle timezone format issues
                    if '+' in event['end_time']:
                        clean_time = event['end_time'].split('+')[0]
                        event['end_time'] = datetime.fromisoformat(clean_time)
                    else:
                        event['end_time'] = datetime.fromisoformat(event['end_time'])
            
            if event['created_at']:
                try:
                    event['created_at'] = datetime.fromisoformat(event['created_at'])
                except ValueError:
                    # Handle timezone format issues
                    if '+' in event['created_at']:
                        clean_time = event['created_at'].split('+')[0]
                        event['created_at'] = datetime.fromisoformat(clean_time)
                    else:
                        event['created_at'] = datetime.fromisoformat(event['created_at'])
            
            logger.info(f"Retrieved latest {event_type} event for thread {thread_id}: {event['id']}")
            return event
        else:
            logger.info(f"No {event_type} events found for thread {thread_id}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving latest event: {str(e)}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def generate_summary(thread_id: str, period: str) -> Dict[str, Any]:
    """
    Generate a summary of routine events for a specific period
    
    Args:
        thread_id: Unique identifier for the conversation thread
        period: Period for the summary ('day', 'week', or 'month')
        
    Returns:
        A dictionary containing summary statistics
    """
    try:
        # Helper function to normalize datetime objects
        def normalize_datetime(dt):
            if dt is None:
                return None
            # If datetime has timezone info, convert to UTC and remove timezone
            if dt.tzinfo is not None:
                from datetime import timezone
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
            
        # Calculate date range based on period
        current_time = datetime.now()
        
        if period == 'day':
            start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            # Use end of day instead of current time
            end_date = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            period_name = "day"
        elif period == 'week':
            # Start from the beginning of the current week (Monday)
            start_date = current_time - timedelta(days=current_time.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = current_time
            period_name = "week"
        elif period == 'month':
            # Start from the beginning of the current month
            start_date = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = current_time
            period_name = "month"
        else:
            logger.error(f"Invalid period: {period}")
            return {"error": f"Invalid period: {period}"}
        
        logger.info(f"Generating summary for thread {thread_id} for period {period} ({start_date} to {end_date})")
        
        # Get all events for the period
        events = get_events_by_date_range(thread_id, start_date, end_date)
        
        # Initialize summary data
        summary = {
            "period": period_name,
            "start_date": start_date,
            "end_date": end_date,
            "sleep": {
                "total_events": 0,
                "total_duration_minutes": 0,
                "average_duration_minutes": 0,
                "events": []
            },
            "feed": {
                "total_events": 0,
                "total_duration_minutes": 0,
                "average_duration_minutes": 0,
                "events": []
            }
        }
        
        # Process events
        sleep_events = [e for e in events if e['event_type'] == 'sleep']
        feed_events = [e for e in events if e['event_type'] == 'feed']
        
        # Filter out potential duplicate events (events with the same start time)
        # This can happen if events were synced multiple times
        unique_sleep_events = []
        seen_sleep_events = set()
        
        # Sort events by start time first to ensure we keep the most recent ones
        for event in sorted(sleep_events, key=lambda x: x['start_time']):
            # Create a key based on start time and end time rounded to the nearest minute
            # This helps catch duplicates even if there are small differences in seconds/microseconds
            start_time_key = event['start_time'].replace(second=0, microsecond=0).isoformat()
            end_time_key = "none" if event['end_time'] is None else event['end_time'].replace(second=0, microsecond=0).isoformat()
            event_key = f"{start_time_key}_{end_time_key}"
            
            # Also check for events with very similar times (within 5 minutes)
            is_duplicate = False
            for existing_event in unique_sleep_events:
                # If start times are within 5 minutes of each other and end times are also similar
                start_diff = abs((existing_event['start_time'] - event['start_time']).total_seconds()) < 300  # 5 minutes
                
                # Check end times if both events have them
                end_diff = False
                if existing_event['end_time'] is not None and event['end_time'] is not None:
                    end_diff = abs((existing_event['end_time'] - event['end_time']).total_seconds()) < 300  # 5 minutes
                elif existing_event['end_time'] is None and event['end_time'] is None:
                    end_diff = True  # Both have no end time
                
                if start_diff and (end_diff or existing_event['end_time'] is None or event['end_time'] is None):
                    is_duplicate = True
                    logger.info(f"Filtering out similar sleep event with start time {event['start_time']} (close to {existing_event['start_time']})")
                    break
            
            if event_key not in seen_sleep_events and not is_duplicate:
                seen_sleep_events.add(event_key)
                unique_sleep_events.append(event)
            else:
                if not is_duplicate:
                    logger.info(f"Filtering out duplicate sleep event with key {event_key}")
        
        # Do the same for feed events
        unique_feed_events = []
        seen_feed_events = set()
        
        for event in sorted(feed_events, key=lambda x: x['start_time']):
            start_time_key = event['start_time'].replace(second=0, microsecond=0).isoformat()
            end_time_key = "none" if event['end_time'] is None else event['end_time'].replace(second=0, microsecond=0).isoformat()
            event_key = f"{start_time_key}_{end_time_key}"
            
            # Also check for events with very similar times (within 5 minutes)
            is_duplicate = False
            for existing_event in unique_feed_events:
                # If start times are within 5 minutes of each other and end times are also similar
                start_diff = abs((existing_event['start_time'] - event['start_time']).total_seconds()) < 300  # 5 minutes
                
                # Check end times if both events have them
                end_diff = False
                if existing_event['end_time'] is not None and event['end_time'] is not None:
                    end_diff = abs((existing_event['end_time'] - event['end_time']).total_seconds()) < 300  # 5 minutes
                elif existing_event['end_time'] is None and event['end_time'] is None:
                    end_diff = True  # Both have no end time
                
                if start_diff and (end_diff or existing_event['end_time'] is None or event['end_time'] is None):
                    is_duplicate = True
                    logger.info(f"Filtering out similar feed event with start time {event['start_time']} (close to {existing_event['start_time']})")
                    break
            
            if event_key not in seen_feed_events and not is_duplicate:
                seen_feed_events.add(event_key)
                unique_feed_events.append(event)
            else:
                if not is_duplicate:
                    logger.info(f"Filtering out duplicate feed event with key {event_key}")
        
        # Use the filtered events for the summary
        sleep_events = unique_sleep_events
        feed_events = unique_feed_events
        
        logger.info(f"Found {len(sleep_events)} sleep events and {len(feed_events)} feed events")
        
        # Process sleep events
        for event in sleep_events:
            summary["sleep"]["total_events"] += 1
            
            # Normalize datetime objects to ensure consistent timezone handling
            start_time = normalize_datetime(event["start_time"])
            end_time = normalize_datetime(event["end_time"])
            
            event_summary = {
                "id": event["id"],  # Include the event ID for tracking
                "start_time": start_time,
                "end_time": end_time,
                "notes": event["notes"]
            }
            
            # Calculate duration if end_time exists
            if end_time and start_time:
                try:
                    # Check if end_time is before start_time (could be overnight sleep or data error)
                    if end_time < start_time:
                        logger.info(f"Detected potential overnight sleep for event {event['id']}: {start_time} to {end_time}")
                        
                        # Check if the end time is from the previous day (data error)
                        if end_time.date() < start_time.date():
                            logger.warning(f"End time is from a previous day for event {event['id']}, adjusting to next day")
                            # Adjust end_time to be on the next day after start_time
                            days_diff = (start_time.date() - end_time.date()).days
                            end_time = end_time + timedelta(days=days_diff + 1)
                        else:
                            # Same day but end_time is earlier than start_time
                            # This could be either:
                            # 1. An overnight sleep (e.g., 22:00 to 06:00)
                            # 2. Events logged out of chronological order (e.g., user meant 09:00 to 12:00 but entered 12:00 to 09:00)
                            
                            # Check if this looks like a typical overnight sleep pattern
                            is_likely_overnight = (start_time.hour >= 20 or start_time.hour <= 3) and (end_time.hour >= 5 and end_time.hour <= 10)
                            
                            if is_likely_overnight:
                                # Normal overnight sleep, add one day to end_time
                                logger.info(f"Treating as overnight sleep for event {event['id']}")
                                end_time = end_time + timedelta(days=1)
                            else:
                                # Likely events entered out of order, swap times
                                logger.warning(f"End time before start time on same day for event {event['id']}, likely entered out of order")
                                # Swap start_time and end_time for duration calculation
                                start_time, end_time = end_time, start_time
                        
                    # Calculate duration with adjusted times
                    duration_minutes = (end_time - start_time).total_seconds() / 60
                    
                    # If duration is unreasonably long (more than 16 hours), it might be a data error
                    if duration_minutes > 16 * 60:
                        logger.warning(f"Unusually long sleep duration for event {event['id']}: {duration_minutes/60:.1f} hours")
                        # Cap at 12 hours as a reasonable maximum
                        duration_minutes = 12 * 60
                    elif duration_minutes > 4 * 60 and start_time.hour >= 8 and start_time.hour <= 18:
                        # If same-day sleep is unusually long (more than 4 hours during day), it might be an error
                        logger.warning(f"Unusually long daytime sleep for event {event['id']}: {duration_minutes/60:.1f} hours")
                        # Cap at 4 hours for daytime naps
                        duration_minutes = 4 * 60
                    
                    # Ensure we don't have negative duration
                    if duration_minutes < 0:
                        logger.warning(f"Negative duration calculated for sleep event {event['id']}, setting to 0")
                        duration_minutes = 0
                        
                    event_summary["duration_minutes"] = duration_minutes
                    summary["sleep"]["total_duration_minutes"] += duration_minutes
                except Exception as e:
                    logger.error(f"Error calculating duration for sleep event {event['id']}: {str(e)}")
                    event_summary["duration_minutes"] = 0
            
            summary["sleep"]["events"].append(event_summary)
        
        # Process feed events
        for event in feed_events:
            summary["feed"]["total_events"] += 1
            
            # Normalize datetime objects to ensure consistent timezone handling
            start_time = normalize_datetime(event["start_time"])
            end_time = normalize_datetime(event["end_time"])
            
            event_summary = {
                "id": event["id"],  # Include the event ID for tracking
                "start_time": start_time,
                "end_time": end_time,
                "notes": event["notes"]
            }
            
            # Calculate duration if end_time exists
            if end_time and start_time:
                try:
                    # Check if this might be overnight feeding (end time earlier than start time)
                    if end_time < start_time:
                        # This is likely overnight feeding
                        # Calculate duration assuming the feeding spans to the next day
                        end_time_next_day = end_time + timedelta(days=1)
                        duration_minutes = (end_time_next_day - start_time).total_seconds() / 60
                        
                        # If duration is unreasonably long (more than 3 hours), it might be a data error
                        if duration_minutes > 3 * 60:
                            logger.warning(f"Unusually long feeding duration for event {event['id']}: {duration_minutes/60:.1f} hours")
                            # Cap at 1 hour as a reasonable maximum
                            duration_minutes = 60
                    else:
                        # Normal same-day feeding
                        duration_minutes = (end_time - start_time).total_seconds() / 60
                    
                    # Ensure we don't have negative duration
                    if duration_minutes < 0:
                        logger.warning(f"Negative duration calculated for feed event {event['id']}, setting to 0")
                        duration_minutes = 0
                        
                    event_summary["duration_minutes"] = duration_minutes
                    summary["feed"]["total_duration_minutes"] += duration_minutes
                except Exception as e:
                    logger.error(f"Error calculating duration for feed event {event['id']}: {str(e)}")
                    event_summary["duration_minutes"] = 0
            
            summary["feed"]["events"].append(event_summary)
        
        # Sort events by start time to ensure they appear in chronological order
        summary["sleep"]["events"] = sorted(summary["sleep"]["events"], key=lambda x: x["start_time"])
        summary["feed"]["events"] = sorted(summary["feed"]["events"], key=lambda x: x["start_time"])
        
        # Calculate averages
        if summary["sleep"]["total_events"] > 0 and summary["sleep"]["total_duration_minutes"] > 0:
            summary["sleep"]["average_duration_minutes"] = summary["sleep"]["total_duration_minutes"] / summary["sleep"]["total_events"]
        
        if summary["feed"]["total_events"] > 0 and summary["feed"]["total_duration_minutes"] > 0:
            summary["feed"]["average_duration_minutes"] = summary["feed"]["total_duration_minutes"] / summary["feed"]["total_events"]
        
        logger.info(f"Summary generated: sleep events={summary['sleep']['total_events']}, feed events={summary['feed']['total_events']}")
        
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return {
            "error": f"Error generating summary: {str(e)}",
            "period": period,
            "start_date": datetime.now(),
            "end_date": datetime.now(),
            "sleep": {"total_events": 0, "events": []},
            "feed": {"total_events": 0, "events": []}
        }

# Initialize the database when the module is imported
init_db() 