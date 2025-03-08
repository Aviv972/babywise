"""
Babywise Assistant - Routines API Router

This module implements the routine-related API endpoints.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.routine_cache import (
    get_cached_routine_summary,
    get_cached_recent_events,
    cache_routine_summary,
    cache_recent_events
)
from backend.db.routine_tracker import (
    add_event,
    update_event,
    get_events_by_date_range,
    get_latest_event
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Request/Response models
class DateRange(BaseModel):
    start_date: date
    end_date: date

class EventCreate(BaseModel):
    thread_id: str
    event_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    notes: Optional[str] = None

class EventUpdate(BaseModel):
    end_time: Optional[datetime] = None
    notes: Optional[str] = None

@router.get("/summary/{thread_id}")
async def get_routine_summary(thread_id: str, period: str = "day"):
    """
    Get a summary of routines for a specific thread
    """
    try:
        # Get summaries for both sleep and feeding events
        sleep_summary = await get_cached_routine_summary(thread_id, "sleep") or {}
        feeding_summary = await get_cached_routine_summary(thread_id, "feeding") or {}
        
        # Get recent events
        sleep_events = await get_cached_recent_events(thread_id, "sleep") or []
        feeding_events = await get_cached_recent_events(thread_id, "feeding") or []
        
        # If no cached data, try to get from database
        if not sleep_summary or not feeding_summary:
            # Calculate date range based on period
            end_date = datetime.now()
            if period == "day":
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                # Start from 7 days ago (including today)
                start_date = (datetime.now() - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "month":
                # Start from 30 days ago (including today)
                start_date = (datetime.now() - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Default to day
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get sleep events from database
            sleep_db_events = await get_events_by_date_range(
                thread_id=thread_id,
                start_date=start_date,
                end_date=end_date,
                event_type="sleep"
            )
            
            # Get sleep_end events from database
            sleep_end_db_events = await get_events_by_date_range(
                thread_id=thread_id,
                start_date=start_date,
                end_date=end_date,
                event_type="sleep_end"
            )
            
            # Get feeding events from database
            feeding_db_events = await get_events_by_date_range(
                thread_id=thread_id,
                start_date=start_date,
                end_date=end_date,
                event_type="feeding"
            )
            
            # Create summaries
            if sleep_db_events:
                # Calculate total sleep duration
                total_sleep_duration = 0
                
                # Log the sleep events for debugging
                logger.info(f"Sleep events for summary: {len(sleep_db_events)}")
                for idx, event in enumerate(sleep_db_events):
                    logger.info(f"Sleep event {idx+1}: start={event.get('start_time')}, end={event.get('end_time')}")
                
                # Log the sleep_end events for debugging
                logger.info(f"Sleep end events for summary: {len(sleep_end_db_events)}")
                for idx, event in enumerate(sleep_end_db_events):
                    logger.info(f"Sleep end event {idx+1}: start={event.get('start_time')}")
                
                # Find the earliest sleep event and the latest sleep_end event
                earliest_sleep = None
                latest_end = None
                
                for event in sleep_db_events:
                    start_time = event.get("start_time")
                    if start_time and (earliest_sleep is None or start_time < earliest_sleep):
                        earliest_sleep = start_time
                
                for event in sleep_db_events:
                    end_time = event.get("end_time")
                    if end_time and (latest_end is None or end_time > latest_end):
                        latest_end = end_time
                
                # If we have both a start and end time, calculate the duration
                if earliest_sleep and latest_end:
                    duration_seconds = (latest_end - earliest_sleep).total_seconds()
                    if duration_seconds > 0:
                        total_sleep_duration = duration_seconds // 60
                        logger.info(f"Calculated sleep duration: {total_sleep_duration} minutes from {earliest_sleep} to {latest_end}")
                
                sleep_summary = {
                    "count": len(sleep_db_events),
                    "total_duration": total_sleep_duration
                }
                sleep_events = sleep_db_events[:5]  # Get 5 most recent events
            
            if feeding_db_events:
                feeding_summary = {
                    "count": len(feeding_db_events),
                    "total_duration": 0  # Feeding doesn't typically have duration
                }
                feeding_events = feeding_db_events[:5]  # Get 5 most recent events
        
        # Ensure we have default values if no data
        if not sleep_summary:
            sleep_summary = {"count": 0, "total_duration": 0}
        
        if not feeding_summary:
            feeding_summary = {"count": 0, "total_duration": 0}
        
        return {
            "summary": {
                "sleep": sleep_summary,
                "feeding": feeding_summary
            },
            "recent_events": {
                "sleep": sleep_events,
                "feeding": feeding_events
            },
            "period": period
        }
    except Exception as e:
        logger.error(f"Error getting routine summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events")
async def create_event(event: EventCreate):
    """Create a new routine event"""
    try:
        event_id = await add_event(
            thread_id=event.thread_id,
            event_type=event.event_type,
            start_time=event.start_time,
            end_time=event.end_time,
            notes=event.notes
        )
        return {"event_id": event_id}
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{event_id}")
async def update_event_endpoint(event_id: int, event_update: EventUpdate):
    """Update an existing routine event"""
    try:
        success = await update_event(
            event_id=event_id,
            end_time=event_update.end_time,
            notes=event_update.notes
        )
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events")
async def get_events(
    thread_id: str,
    start_date: datetime,
    end_date: datetime,
    event_type: Optional[str] = None
):
    """Get events for a specific thread within a date range"""
    try:
        events = await get_events_by_date_range(
            thread_id=thread_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type
        )
        return {"events": events}
    except Exception as e:
        logger.error(f"Error getting events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/latest/{thread_id}/{event_type}")
async def get_latest_event_endpoint(thread_id: str, event_type: str):
    """Get the most recent event of a specific type"""
    try:
        event = await get_latest_event(thread_id=thread_id, event_type=event_type)
        if not event:
            return {"event": None}
        return {"event": event}
    except Exception as e:
        logger.error(f"Error getting latest event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 