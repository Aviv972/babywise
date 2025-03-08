"""
Babywise Chatbot - Command Processor Pipeline

This module implements a separate pipeline for processing routine tracking commands,
handling events like sleep and feeding independently from the chat workflow.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from backend.workflow.command_parser import detect_command
from backend.db.routine_tracker import add_event, get_events_by_date_range, generate_summary
from backend.services.redis_service import (
    cache_routine_summary,
    get_cached_routine_summary,
    cache_recent_events,
    get_cached_recent_events
)
from backend.services.analytics_service import (
    update_daily_stats,
    update_weekly_stats,
    update_pattern_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandProcessor:
    def __init__(self):
        self.last_event = None
    
    async def process_command(self, message: str, thread_id: str = "default") -> Dict[str, Any]:
        """
        Process a command message and return the appropriate response
        
        Args:
            message: The user message to process
            thread_id: The conversation thread ID
            
        Returns:
            Dictionary containing the response and any relevant data
        """
        # Log the incoming message
        logger.info(f"Processing potential command: '{message}' for thread {thread_id}")
        
        # Detect command type
        command = detect_command(message)
        if not command:
            logger.info(f"No command detected in message: '{message}'")
            return {
                "success": False,
                "message": "No command detected",
                "response_type": "error"
            }
        
        # Add thread_id to command
        command["thread_id"] = thread_id
        logger.info(f"Detected command: {command}")
        
        try:
            if command["command_type"] == "event":
                return await self._handle_event(command)
            elif command["command_type"] == "summary":
                return await self._handle_summary(command)
            elif command["command_type"] == "help":
                return self._handle_help(command)
            else:
                logger.warning(f"Unknown command type: {command['command_type']}")
                return {
                    "success": False,
                    "message": "Unknown command type",
                    "response_type": "error"
                }
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing command: {str(e)}",
                "response_type": "error"
            }
    
    async def _handle_event(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sleep or feeding event commands"""
        thread_id = command["thread_id"]
        event_type = command["event_type"]
        action = command["action"]
        time = command["time"]
        notes = command.get("notes", "")
        
        logger.info(f"Handling {event_type} event for thread {thread_id}: {action} at {time}")
        
        try:
            # Add event to database
            event_id = await add_event(
                thread_id=thread_id,
                event_type=event_type,
                start_time=time,
                end_time=None if action == "start" else time,
                notes=notes
            )
            
            # Create event data
            event_data = {
                "id": event_id,
                "thread_id": thread_id,
                "type": event_type,
                "action": action,
                "timestamp": time.isoformat(),
                "notes": notes
            }
            
            # Store last event for context
            self.last_event = event_data
            
            # Generate response
            response = self._generate_event_response(command)
            logger.info(f"Generated response for {event_type} event: {response}")
            
            return {
                "success": True,
                "message": response,
                "response_type": "event_confirmation",
                "event_data": event_data
            }
        except Exception as e:
            logger.error(f"Error handling event: {str(e)}")
            raise
    
    async def _handle_summary(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle summary request commands"""
        thread_id = command["thread_id"]
        period = command.get("period", "day")
        
        logger.info(f"Handling summary request for thread {thread_id}, period: {period}")
        
        try:
            # Generate summary from database
            summary = await generate_summary(thread_id, None, period)
            
            if not summary:
                # No data available
                if command["language"] == "he":
                    message = "אין מספיק נתונים כדי ליצור סיכום. נסה לתעד כמה אירועים קודם."
                else:
                    message = "Not enough data to generate a summary. Try recording some events first."
                
                return {
                    "success": True,
                    "message": message,
                    "response_type": "summary",
                    "summary_data": {}
                }
            
            # Generate response
            response = self._generate_summary_response(summary, command["language"])
            logger.info(f"Generated summary response: {response[:100]}...")
            
            return {
                "success": True,
                "message": response,
                "response_type": "summary",
                "summary_data": summary
            }
        except Exception as e:
            logger.error(f"Error handling summary: {str(e)}")
            raise
    
    def _handle_help(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help request commands"""
        language = command["language"]
        help_text = self._generate_help_text(language)
        return {
            "success": True,
            "message": help_text,
            "response_type": "help"
        }
    
    def _generate_event_response(self, command: Dict[str, Any]) -> str:
        """Generate a response message for an event command"""
        event_type = command["event_type"]
        action = command["action"]
        time = command["time"]
        language = command["language"]
        
        if language == "he":
            if event_type == "sleep":
                if action == "start":
                    return f"רשמתי שהתינוק התחיל לישון ב-{time.strftime('%H:%M')}"
                else:
                    return f"רשמתי שהתינוק התעורר ב-{time.strftime('%H:%M')}"
            else:  # feeding
                if action == "start":
                    return f"רשמתי שהתינוק התחיל לאכול ב-{time.strftime('%H:%M')}"
                else:
                    return f"רשמתי שהתינוק סיים לאכול ב-{time.strftime('%H:%M')}"
        else:
            if event_type == "sleep":
                if action == "start":
                    return f"Recorded sleep start at {time.strftime('%I:%M %p')}"
                else:
                    return f"Recorded wake up at {time.strftime('%I:%M %p')}"
            else:  # feeding
                if action == "start":
                    return f"Recorded feeding start at {time.strftime('%I:%M %p')}"
                else:
                    return f"Recorded feeding end at {time.strftime('%I:%M %p')}"
    
    def _generate_summary_response(self, summary_data: Dict[str, Any], language: str) -> str:
        """Generate a response message for a summary command"""
        if language == "he":
            return self._generate_hebrew_summary(summary_data)
        return self._generate_english_summary(summary_data)
    
    def _generate_english_summary(self, summary_data: Dict[str, Any]) -> str:
        """Generate an English summary response"""
        period = summary_data.get("period", "day")
        period_name = "Today" if period == "day" else "This Week" if period == "week" else "This Month"
        
        response = f"**Baby Routine Summary for {period_name}**\n\n"
        
        # Process routines
        routines = summary_data.get("routines", {})
        
        # Sleep summary
        if "sleep" in routines:
            sleep_data = routines["sleep"]
            response += "**Sleep:**\n"
            response += f"- Total sleep events: {sleep_data.get('total_events', 0)}\n"
            
            if sleep_data.get('total_duration') is not None:
                response += f"- Total sleep time: {sleep_data.get('total_duration', 0):.1f} hours\n"
            
            if sleep_data.get('average_duration') is not None:
                response += f"- Average sleep duration: {sleep_data.get('average_duration', 0):.1f} hours\n"
            
            # Latest sleep event
            if sleep_data.get('latest_event'):
                latest = sleep_data['latest_event']
                start_time = latest.get('start_time', '')
                
                # Handle datetime object or string
                if isinstance(start_time, datetime):
                    start_time_str = start_time.strftime("%Y-%m-%d at %I:%M %p")
                elif isinstance(start_time, str) and 'T' in start_time:
                    date_part = start_time.split('T')[0]
                    time_part = start_time.split('T')[1][:5]
                    start_time_str = f"{date_part} at {time_part}"
                else:
                    start_time_str = str(start_time)
                
                response += f"- Latest sleep: {start_time_str}\n"
        
        # Feeding summary
        if "feeding" in routines:
            feeding_data = routines["feeding"]
            response += "\n**Feeding:**\n"
            response += f"- Total feedings: {feeding_data.get('total_events', 0)}\n"
            
            if feeding_data.get('average_duration') is not None:
                response += f"- Average feeding duration: {feeding_data.get('average_duration', 0) * 60:.0f} minutes\n"
            
            # Latest feeding event
            if feeding_data.get('latest_event'):
                latest = feeding_data['latest_event']
                start_time = latest.get('start_time', '')
                
                # Handle datetime object or string
                if isinstance(start_time, datetime):
                    start_time_str = start_time.strftime("%Y-%m-%d at %I:%M %p")
                elif isinstance(start_time, str) and 'T' in start_time:
                    date_part = start_time.split('T')[0]
                    time_part = start_time.split('T')[1][:5]
                    start_time_str = f"{date_part} at {time_part}"
                else:
                    start_time_str = str(start_time)
                
                response += f"- Latest feeding: {start_time_str}\n"
        
        return response
    
    def _generate_hebrew_summary(self, summary_data: Dict[str, Any]) -> str:
        """Generate a Hebrew summary response"""
        period = summary_data.get("period", "day")
        period_name = "היום" if period == "day" else "השבוע" if period == "week" else "החודש"
        
        response = f"**סיכום שגרת תינוק ל{period_name}**\n\n"
        
        # Process routines
        routines = summary_data.get("routines", {})
        
        # Sleep summary
        if "sleep" in routines:
            sleep_data = routines["sleep"]
            response += "**שינה:**\n"
            response += f"- סך הכל אירועי שינה: {sleep_data.get('total_events', 0)}\n"
            
            if sleep_data.get('total_duration') is not None:
                hours = int(sleep_data.get('total_duration', 0))
                minutes = int((sleep_data.get('total_duration', 0) - hours) * 60)
                response += f"- סך הכל זמן שינה: {hours}ש {minutes}ד\n"
            
            if sleep_data.get('average_duration') is not None:
                avg_hours = int(sleep_data.get('average_duration', 0))
                avg_minutes = int((sleep_data.get('average_duration', 0) - avg_hours) * 60)
                response += f"- משך שינה ממוצע: {avg_hours}ש {avg_minutes}ד\n"
            
            # Latest sleep event
            if sleep_data.get('latest_event'):
                latest = sleep_data['latest_event']
                start_time = latest.get('start_time', '')
                
                # Handle datetime object or string
                if isinstance(start_time, datetime):
                    start_time_str = start_time.strftime("%Y-%m-%d בשעה %H:%M")
                elif isinstance(start_time, str) and 'T' in start_time:
                    date_part = start_time.split('T')[0]
                    time_part = start_time.split('T')[1][:5]
                    start_time_str = f"{date_part} בשעה {time_part}"
                else:
                    start_time_str = str(start_time)
                
                response += f"- שינה אחרונה: {start_time_str}\n"
        
        # Feeding summary
        if "feeding" in routines:
            feeding_data = routines["feeding"]
            response += "\n**האכלה:**\n"
            response += f"- סך הכל האכלות: {feeding_data.get('total_events', 0)}\n"
            
            if feeding_data.get('average_duration') is not None:
                avg_minutes = int(feeding_data.get('average_duration', 0) * 60)
                response += f"- משך האכלה ממוצע: {avg_minutes}ד\n"
            
            # Latest feeding event
            if feeding_data.get('latest_event'):
                latest = feeding_data['latest_event']
                start_time = latest.get('start_time', '')
                
                # Handle datetime object or string
                if isinstance(start_time, datetime):
                    start_time_str = start_time.strftime("%Y-%m-%d בשעה %H:%M")
                elif isinstance(start_time, str) and 'T' in start_time:
                    date_part = start_time.split('T')[0]
                    time_part = start_time.split('T')[1][:5]
                    start_time_str = f"{date_part} בשעה {time_part}"
                else:
                    start_time_str = str(start_time)
                
                response += f"- האכלה אחרונה: {start_time_str}\n"
        
        return response
    
    def _generate_help_text(self, language: str) -> str:
        """Generate help text in the specified language"""
        if language == "he":
            return """איך להשתמש במעקב שגרה:

1. רישום שינה:
   - "התינוק הלך לישון ב-9:30"
   - "התעורר ב-11:00"

2. רישום האכלה:
   - "התחיל לאכול ב-10:00"
   - "סיים לאכול ב-10:20"

3. בקשת סיכום:
   - "תראה לי סיכום של היום"
   - "סיכום שבועי"
"""
        else:
            return """How to use routine tracking:

1. Recording sleep:
   - "baby went to sleep at 9:30"
   - "woke up at 11:00"

2. Recording feeding:
   - "started feeding at 10:00"
   - "finished feeding at 10:20"

3. Getting summaries:
   - "show me today's summary"
   - "weekly summary"
""" 