"""
Babywise Chatbot - Post Processing

This module implements the post-processing workflow node for the Babywise Chatbot.
It handles command parsing for routine tracking and summary commands.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re
import requests
import aiohttp
from backend.models.message_types import AIMessage, HumanMessage
from .command_parser import detect_command, extract_notes, get_help_text, format_summary_response
from ..db.routine_tracker import (
    add_event, 
    update_event, 
    get_events_by_date_range, 
    get_latest_event,
    generate_summary
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
api_url = "http://localhost:8080/api/routine/process-command"

async def post_process(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process the state after response generation
    
    Args:
        state: The current conversation state
        
    Returns:
        The updated state
    """
    try:
        # Add timestamp to metadata
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"]["processed_at"] = datetime.now().isoformat()
        
        # Get the latest user message
        messages = state.get("messages", [])
        latest_user_message = None
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                latest_user_message = message.content
                break
        
        if latest_user_message:
            logger.info(f"Checking for commands in message: '{latest_user_message}'")
            # Detect command
            command = detect_command(latest_user_message)
            
            if command:
                logger.info(f"Command detected: {json.dumps(command, default=str)}")
                try:
                    # Get thread_id from state
                    thread_id = state["metadata"].get("thread_id", "default")
                    language = state.get("language", "en")
                    
                    # Try API call first
                    api_success = False
                    try:
                        # Use the API endpoint for command processing
                        payload = {
                            "thread_id": thread_id,
                            "message": latest_user_message,
                            "language": language
                        }
                        
                        logger.info(f"Calling command processing API with payload: {json.dumps(payload, default=str)}")
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.post(api_url, json=payload) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    logger.info(f"Command API response: {json.dumps(result, default=str)}")
                                    
                                    if result.get("status") == "success" and result.get("response"):
                                        # Update the state with the command response
                                        state["messages"].append(AIMessage(content=result["response"]))
                                        state["metadata"]["command_processed"] = True
                                        logger.info(f"Command processed successfully via API, response: '{result['response']}'")
                                        api_success = True
                                    else:
                                        logger.warning(f"Command API returned error: {result.get('message', 'Unknown error')}")
                                else:
                                    logger.error(f"Command API request failed with status {response.status}: {await response.text()}")
                    except Exception as api_error:
                        logger.error(f"Error calling command API: {str(api_error)}", exc_info=True)
                    
                    # If API call failed, process command directly
                    if not api_success:
                        logger.info("API call failed, processing command directly")
                        command_response = await process_command(command, state, latest_user_message)
                        
                        if command_response:
                            logger.info(f"Command processed with fallback, response: '{command_response}'")
                            # Update the state with the command response
                            state["messages"].append(AIMessage(content=command_response))
                            state["metadata"]["command_processed"] = True
                            return state
                        else:
                            logger.warning("Command processed with fallback but no response generated")
                    
                    return state
                
                except Exception as e:
                    logger.error(f"Error processing command: {str(e)}", exc_info=True)
            else:
                logger.info("No command detected in message")
        
        # Log the state summary for debugging
        logger.info("Post-processing complete - State summary:")
        logger.info(f"  Domain: {state.get('domain', 'unknown')}")
        logger.info(f"  Messages: {len(state.get('messages', []))}")
        logger.info(f"  Context: {json.dumps(state.get('context', {}), default=str)}")
        
        return state
    except Exception as e:
        logger.error(f"Error in post-processing: {str(e)}", exc_info=True)
        return state

async def process_command(command: Dict[str, Any], state: Dict[str, Any], message: str) -> Optional[str]:
    """
    Process a detected command
    
    Args:
        command: The command dictionary
        state: The current conversation state
        message: The original user message
        
    Returns:
        A response message, or None if no response needed
    """
    try:
        logger.info(f"Processing command: {json.dumps(command, default=str)}")
        thread_id = state["metadata"].get("thread_id", "default")
        logger.info(f"Thread ID from state metadata: {thread_id}")
        command_type = command.get("command_type")
        language = command.get("language", state.get("language", "en"))
        
        if command_type == "event":
            logger.info(f"Calling process_event_command for {command.get('event_type')} {command.get('action')}")
            return process_event_command(command, state, message)
        elif command_type == "summary":
            logger.info(f"Calling process_summary_command for period {command.get('period', 'day')}")
            return await process_summary_command(command, thread_id, language)
        elif command_type == "help":
            logger.info(f"Getting help text in language {language}")
            return get_help_text(language)
        else:
            logger.warning(f"Unknown command type: {command_type}")
            return None
    
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}", exc_info=True)
        if command.get("language") == "he":
            return f"אני מצטער, נתקלתי בשגיאה בעת עיבוד פקודת המעקב שלך: {str(e)}"
        else:
            return f"I'm sorry, I encountered an error while processing your tracking command: {str(e)}"

def process_event_command(command: Dict[str, Any], state: Dict[str, Any], message: str) -> str:
    """
    Process an event command (sleep or feeding tracking)
    
    Args:
        command: The command dictionary
        state: The current conversation state
        message: The original user message
        
    Returns:
        A response message
    """
    event_type = command.get('event_type')
    action = command.get('action')
    event_time = command.get('time')
    thread_id = state.get('metadata', {}).get('thread_id', 'unknown')
    language = command.get('language', state.get('language', 'en'))
    
    logger.info(f"Processing {event_type} {action} command for thread {thread_id} in language {language}")
    logger.info(f"Event time: {event_time}")
    logger.info(f"Thread ID from state: {thread_id}")
    
    # Extract notes if any
    notes = extract_notes(message, command)
    
    # Auto-status management: If starting a feeding event, check for ongoing sleep
    auto_ended_sleep = False
    auto_ended_feed = False
    
    if event_type == 'feeding' and action == 'start':
        # Check if there's an ongoing sleep event
        latest_sleep = get_latest_event(thread_id, 'sleep')
        logger.info(f"Latest sleep event for thread {thread_id}: {json.dumps(latest_sleep, default=str) if latest_sleep else 'None'}")
        
        if latest_sleep and latest_sleep.get('end_time') is None:
            # Automatically end the sleep event
            logger.info(f"Auto-ending sleep event {latest_sleep['id']} due to feeding start")
            auto_note = "Automatically ended due to feeding event"
            
            # Combine with existing notes if any
            combined_notes = auto_note
            if latest_sleep.get('notes'):
                combined_notes = f"{latest_sleep.get('notes')}; {auto_note}"
            
            # Update the sleep event with end time
            success = update_event(
                event_id=latest_sleep['id'],
                end_time=event_time,
                notes=combined_notes
            )
            
            if success:
                auto_ended_sleep = True
                logger.info(f"Successfully auto-ended sleep event {latest_sleep['id']}")
                # Calculate sleep duration for logging
                sleep_start = latest_sleep['start_time']
                sleep_duration_minutes = (event_time - sleep_start).total_seconds() / 60
                logger.info(f"Auto-ended sleep duration: {sleep_duration_minutes:.1f} minutes")
            else:
                logger.error(f"Failed to auto-end sleep event {latest_sleep['id']}")
    
    # Auto-status management: If starting a sleep event, check for ongoing feeding
    elif event_type == 'sleep' and action == 'start':
        # Check if there's an ongoing feeding event
        latest_feed = get_latest_event(thread_id, 'feeding')
        
        if latest_feed and latest_feed.get('end_time') is None:
            # Automatically end the feeding event
            logger.info(f"Auto-ending feeding event {latest_feed['id']} due to sleep start")
            auto_note = "Automatically ended due to sleep event"
            
            # Combine with existing notes if any
            combined_notes = auto_note
            if latest_feed.get('notes'):
                combined_notes = f"{latest_feed.get('notes')}; {auto_note}"
            
            # Update the feeding event with end time
            success = update_event(
                event_id=latest_feed['id'],
                end_time=event_time,
                notes=combined_notes
            )
            
            if success:
                auto_ended_feed = True
                logger.info(f"Successfully auto-ended feeding event {latest_feed['id']}")
                # Calculate feeding duration for logging
                feed_start = latest_feed['start_time']
                feed_duration_minutes = (event_time - feed_start).total_seconds() / 60
                logger.info(f"Auto-ended feeding duration: {feed_duration_minutes:.1f} minutes")
            else:
                logger.error(f"Failed to auto-end feeding event {latest_feed['id']}")
    
    # Process the event based on action
    try:
        if action == 'start':
            # Add a new event
            event_id = add_event(
                thread_id=thread_id,
                event_type=event_type,
                start_time=event_time,
                notes=notes
            )
            
            logger.info(f"Added {event_type} event with ID {event_id}")
            
            # Generate response based on language
            if language == "he":
                if event_type == 'sleep':
                    response = f"רשמתי שהתינוק הלך לישון ב-{event_time.strftime('%H:%M')}."
                    if auto_ended_feed:
                        response += f" סיימתי אוטומטית את אירוע ההאכלה הקודם."
                else:  # feeding
                    response = f"רשמתי שהתינוק התחיל לאכול ב-{event_time.strftime('%H:%M')}."
                    if auto_ended_sleep:
                        response += f" סיימתי אוטומטית את אירוע השינה הקודם."
            else:  # en
                if event_type == 'sleep':
                    response = f"I've logged that your baby went to sleep at {event_time.strftime('%I:%M %p')}."
                    if auto_ended_feed:
                        response += f" I've automatically ended the previous feeding event."
                else:  # feeding
                    response = f"I've logged that your baby started feeding at {event_time.strftime('%I:%M %p')}."
                    if auto_ended_sleep:
                        response += f" I've automatically ended the previous sleep event."
            
            return response
            
        elif action == 'end':
            # Find the latest event of this type for the thread
            latest_event = get_latest_event(thread_id, event_type)
            
            if latest_event and latest_event.get('end_time') is None:
                # Update the event with end time
                success = update_event(
                    event_id=latest_event['id'],
                    end_time=event_time,
                    notes=notes
                )
                
                if success:
                    logger.info(f"Updated {event_type} event {latest_event['id']} with end time {event_time}")
                    
                    # Calculate duration
                    start_time = latest_event['start_time']
                    duration_minutes = (event_time - start_time).total_seconds() / 60
                    
                    # Generate response based on language
                    if language == "he":
                        if event_type == 'sleep':
                            response = f"רשמתי שהתינוק התעורר ב-{event_time.strftime('%H:%M')}. משך השינה היה {duration_minutes:.1f} דקות."
                        else:  # feeding
                            response = f"רשמתי שהתינוק סיים לאכול ב-{event_time.strftime('%H:%M')}. משך ההאכלה היה {duration_minutes:.1f} דקות."
                    else:  # en
                        if event_type == 'sleep':
                            response = f"I've logged that your baby woke up at {event_time.strftime('%I:%M %p')}. The sleep duration was {duration_minutes:.1f} minutes."
                        else:  # feeding
                            response = f"I've logged that your baby finished feeding at {event_time.strftime('%I:%M %p')}. The feeding duration was {duration_minutes:.1f} minutes."
                    
                    return response
                else:
                    logger.error(f"Failed to update {event_type} event {latest_event['id']}")
                    
                    if language == "he":
                        return f"אני מצטער, נתקלתי בשגיאה בעת עדכון אירוע ה{event_type}."
                    else:
                        return f"I'm sorry, I encountered an error while updating the {event_type} event."
            else:
                # For sleep events, check if there's any sleep event in the last 12 hours
                if event_type == 'sleep':
                    # Get all sleep events from the last 12 hours
                    recent_events = get_events_by_date_range(thread_id, event_type, 'day')
                    
                    # Filter to find events in the last 12 hours
                    twelve_hours_ago = event_time - timedelta(hours=12)
                    recent_sleep_events = [
                        e for e in recent_events 
                        if e['start_time'] >= twelve_hours_ago and e['end_time'] is None
                    ]
                    
                    # If we found any recent sleep events without end time, use the most recent one
                    if recent_sleep_events:
                        # Sort by start time descending to get the most recent
                        recent_sleep_events.sort(key=lambda x: x['start_time'], reverse=True)
                        latest_sleep = recent_sleep_events[0]
                        
                        # Update this event instead of creating a new one
                        success = update_event(
                            event_id=latest_sleep['id'],
                            end_time=event_time,
                            notes=f"End time added from wake-up command; {notes}" if notes else "End time added from wake-up command"
                        )
                        
                        if success:
                            logger.info(f"Updated recent sleep event {latest_sleep['id']} with end time {event_time}")
                            
                            # Calculate duration
                            start_time = latest_sleep['start_time']
                            duration_minutes = (event_time - start_time).total_seconds() / 60
                            
                            # Generate response based on language
                            if language == "he":
                                response = f"רשמתי שהתינוק התעורר ב-{event_time.strftime('%H:%M')}. משך השינה היה {duration_minutes:.1f} דקות."
                            else:  # en
                                response = f"I've logged that your baby woke up at {event_time.strftime('%I:%M %p')}. The sleep duration was {duration_minutes:.1f} minutes."
                            
                            return response
                
                # No ongoing event found, create a new one with both start and end times
                # Assume the event started 30 minutes ago for sleep, 15 minutes ago for feeding
                if event_type == 'sleep':
                    assumed_start_time = event_time - timedelta(minutes=30)
                else:  # feeding
                    assumed_start_time = event_time - timedelta(minutes=15)
                
                event_id = add_event(
                    thread_id=thread_id,
                    event_type=event_type,
                    start_time=assumed_start_time,
                    end_time=event_time,
                    notes=f"Auto-created with assumed start time; {notes}" if notes else "Auto-created with assumed start time"
                )
                
                logger.info(f"Created {event_type} event {event_id} with assumed start time {assumed_start_time}")
                
                # Calculate duration
                duration_minutes = (event_time - assumed_start_time).total_seconds() / 60
                
                # Generate response based on language
                if language == "he":
                    if event_type == 'sleep':
                        response = f"לא מצאתי אירוע שינה פעיל, אז יצרתי אחד חדש. רשמתי שהתינוק ישן מ-{assumed_start_time.strftime('%H:%M')} עד {event_time.strftime('%H:%M')}. משך השינה המשוער היה {duration_minutes:.1f} דקות."
                    else:  # feeding
                        response = f"לא מצאתי אירוע האכלה פעיל, אז יצרתי אחד חדש. רשמתי שהתינוק אכל מ-{assumed_start_time.strftime('%H:%M')} עד {event_time.strftime('%H:%M')}. משך ההאכלה המשוער היה {duration_minutes:.1f} דקות."
                else:  # en
                    if event_type == 'sleep':
                        response = f"I didn't find an active sleep event, so I created a new one. I've logged that your baby slept from {assumed_start_time.strftime('%I:%M %p')} to {event_time.strftime('%I:%M %p')}. The estimated sleep duration was {duration_minutes:.1f} minutes."
                    else:  # feeding
                        response = f"I didn't find an active feeding event, so I created a new one. I've logged that your baby fed from {assumed_start_time.strftime('%I:%M %p')} to {event_time.strftime('%I:%M %p')}. The estimated feeding duration was {duration_minutes:.1f} minutes."
                
                return response
        
        else:
            logger.warning(f"Unknown action: {action}")
            
            if language == "he":
                return "אני מצטער, לא הבנתי את הפקודה. נסה 'התינוק הלך לישון ב-8:30' או 'התינוק התעורר ב-6:00'."
            else:
                return "I'm sorry, I didn't understand the command. Try 'Baby went to sleep at 8:30pm' or 'Baby woke up at 6:00am'."
    
    except Exception as e:
        logger.error(f"Error processing {event_type} {action} command: {str(e)}", exc_info=True)
        
        if language == "he":
            return f"אני מצטער, נתקלתי בשגיאה בעת עיבוד פקודת המעקב שלך: {str(e)}"
        else:
            return f"I'm sorry, I encountered an error while processing your tracking command: {str(e)}"

async def process_summary_command(command: Dict[str, Any], thread_id: str, language: str) -> str:
    """
    Process a summary command
    
    Args:
        command: The command dictionary
        thread_id: The conversation thread ID
        language: The language code (e.g., 'en', 'he')
        
    Returns:
        A formatted summary response
    """
    period = command.get('period', 'day')
    
    try:
        # Generate summary - make sure to await the coroutine
        summary = await generate_summary(thread_id, None, period)
        
        # Add language to summary for formatting
        summary["language"] = language
        
        # Format the summary into a readable response
        return format_summary_response(summary)
    except Exception as e:
        logger.error(f"Error processing summary command: {str(e)}", exc_info=True)
        if language == "he":
            return f"אני מצטער, נתקלתי בשגיאה בעת עיבוד פקודת הסיכום: {str(e)}"
        else:
            return f"I'm sorry, I encountered an error while processing your summary command: {str(e)}" 