"""
Babywise Chatbot - Routine Tracker API Endpoints

This module implements the FastAPI endpoints for the Baby Routine Tracker feature,
allowing access to routine events via REST API.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field

from backend.db.routine_tracker import (
    add_event, 
    update_event, 
    get_events_by_date_range, 
    delete_event,
    get_latest_event,
    generate_summary
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/routines", tags=["routines"])

# Pydantic models for request/response
class EventCreate(BaseModel):
    thread_id: str = Field(..., description="Unique identifier for the conversation thread")
    event_type: str = Field(..., description="Type of event (e.g., 'sleep', 'feed')")
    start_time: datetime = Field(..., description="Start time of the event")
    end_time: Optional[datetime] = Field(None, description="End time of the event (optional)")
    notes: Optional[str] = Field(None, description="Additional notes about the event")

class EventUpdate(BaseModel):
    end_time: Optional[datetime] = Field(None, description="New end time for the event")
    notes: Optional[str] = Field(None, description="New notes for the event")

class EventResponse(BaseModel):
    id: int
    thread_id: str
    event_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class SummaryResponse(BaseModel):
    period: str
    start_date: datetime
    end_date: datetime
    total_events: int
    routines: Dict[str, Any]

# Endpoints
@router.post("/events", response_model=Dict[str, Any], status_code=201)
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
        
        return {
            "success": True,
            "message": f"Event created successfully",
            "event_id": event_id
        }
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")

@router.get("/events", response_model=List[EventResponse])
async def get_events(
    thread_id: str = Query(..., description="Thread ID to filter events"),
    start_date: datetime = Query(..., description="Start date for filtering events"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering events"),
    event_type: Optional[str] = Query(None, description="Event type to filter (e.g., 'sleep', 'feed')")
):
    """Get events for a specific thread within a date range"""
    try:
        # If end_date is not provided, use current time
        if end_date is None:
            end_date = datetime.now()
            
        events = get_events_by_date_range(
            thread_id=thread_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type
        )
        
        return events
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {str(e)}")

@router.put("/events/{event_id}", response_model=Dict[str, Any])
async def update_event_endpoint(
    event_id: int = Path(..., description="ID of the event to update"),
    event_update: EventUpdate = None
):
    """Update an existing routine event"""
    try:
        success = await update_event(
            event_id=event_id,
            end_time=event_update.end_time if event_update else None,
            notes=event_update.notes if event_update else None
        )
        
        if success:
            return {
                "success": True,
                "message": f"Event {event_id} updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found or no changes made")
    except Exception as e:
        logger.error(f"Error updating event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating event: {str(e)}")

@router.delete("/events/{event_id}", response_model=Dict[str, Any])
async def delete_event_endpoint(
    event_id: int = Path(..., description="ID of the event to delete")
):
    """Delete a routine event"""
    try:
        success = await delete_event(event_id)
        
        if success:
            return {
                "success": True,
                "message": f"Event {event_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    except Exception as e:
        logger.error(f"Error deleting event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")

@router.get("/summary/{thread_id}", response_model=SummaryResponse)
async def get_summary(
    thread_id: str = Path(..., description="Thread ID to generate summary for"),
    period: str = Query("day", description="Period for the summary ('day', 'week', or 'month')")
):
    """Generate a summary of routine events for a specific period"""
    try:
        if period not in ["day", "week", "month"]:
            raise HTTPException(status_code=400, detail=f"Invalid period: {period}. Must be 'day', 'week', or 'month'")
        
        # Use the routines.py implementation which handles both sleep and feeding
        from backend.api.routines import get_routine_summary
        summary = await get_routine_summary(thread_id, period)
        
        if isinstance(summary, dict) and "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
            
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@router.get("/latest/{thread_id}/{event_type}", response_model=Optional[EventResponse])
async def get_latest_event_endpoint(
    thread_id: str = Path(..., description="Thread ID to get latest event for"),
    event_type: str = Path(..., description="Type of event to retrieve")
):
    """Get the latest event of a specific type for a thread"""
    try:
        event = await get_latest_event(thread_id, event_type)
        return event
    except Exception as e:
        logger.error(f"Error getting latest event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting latest event: {str(e)}")

# New endpoint for testing command processing
class CommandTestRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID for the command")
    message: str = Field(..., description="Message containing the command")
    language: str = Field("he", description="Language of the command")

@router.post("/test-command", response_model=Dict[str, Any])
async def test_command_processing(request: CommandTestRequest):
    """Test endpoint for command processing"""
    try:
        from backend.workflow.command_parser import detect_command
        from backend.workflow.post_process import process_command
        
        # Detect command
        command = detect_command(request.message)
        
        if not command:
            return {"status": "error", "message": "No command detected in the message"}
        
        # Create a minimal state for processing
        state = {
            "metadata": {
                "thread_id": request.thread_id
            },
            "language": request.language
        }
        
        # Process the command
        response = await process_command(command, state, request.message)
        
        # Check the database for the event
        if command.get("command_type") == "event":
            event_type = command.get("event_type")
            latest_event = await get_latest_event(request.thread_id, event_type)
            
            return {
                "status": "success",
                "command_detected": command,
                "response": response,
                "latest_event": latest_event
            }
        
        return {
            "status": "success",
            "command_detected": command,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error in test command processing: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

# New endpoint for direct command processing
class DirectCommandRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID for the command")
    message: str = Field(..., description="Message containing the command")
    language: str = Field("he", description="Language of the command")

@router.post("/process-command", response_model=Dict[str, Any])
async def process_direct_command(request: DirectCommandRequest):
    """Process a command directly from the chat interface"""
    try:
        from backend.workflow.command_parser import detect_command
        from backend.workflow.post_process import process_command
        
        # Detect command
        command = detect_command(request.message)
        
        if not command:
            return {"status": "error", "message": "No command detected in the message"}
        
        # Create a minimal state for processing
        state = {
            "metadata": {
                "thread_id": request.thread_id
            },
            "language": request.language
        }
        
        # Process the command
        response = await process_command(command, state, request.message)
        
        # Check the database for the event if it's an event command
        if command.get("command_type") == "event":
            event_type = command.get("event_type")
            latest_event = await get_latest_event(request.thread_id, event_type)
            
            return {
                "status": "success",
                "command_detected": command,
                "response": response,
                "latest_event": latest_event
            }
        
        return {
            "status": "success",
            "command_detected": command,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error processing command: {str(e)}"}

@router.post("/command", response_model=Dict[str, Any])
async def process_routine_command(request: DirectCommandRequest):
    """Process a routine command directly from the frontend"""
    try:
        from backend.workflow.command_parser import detect_command
        from backend.workflow.post_process import process_command
        
        # Detect command
        command = detect_command(request.message)
        
        if not command:
            return {
                "status": "error", 
                "message": "No command detected in the message",
                "should_fallback_to_chat": True  # Indicate that this should be processed as a chat message
            }
        
        # Create a minimal state for processing
        state = {
            "metadata": {
                "thread_id": request.thread_id
            },
            "language": request.language
        }
        
        # Process the command
        response = await process_command(command, state, request.message)
        
        # Check the database for the event if it's an event command
        if command.get("command_type") == "event":
            event_type = command.get("event_type")
            latest_event = await get_latest_event(request.thread_id, event_type)
            
            return {
                "status": "success",
                "command_detected": command,
                "response": response,
                "latest_event": latest_event,
                "should_fallback_to_chat": False  # Don't process as chat
            }
        
        return {
            "status": "success",
            "command_detected": command,
            "response": response,
            "should_fallback_to_chat": False  # Don't process as chat
        }
    except Exception as e:
        logger.error(f"Error processing routine command: {str(e)}", exc_info=True)
        return {
            "status": "error", 
            "message": f"Error processing command: {str(e)}",
            "should_fallback_to_chat": True  # Fallback to chat on error
        } 