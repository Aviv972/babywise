"""
Babywise Chatbot - Command Parser

This module implements the command parser for the Baby Routine Tracker feature,
detecting and processing commands in user messages for tracking sleep, feeding, and other events.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command patterns - English
SLEEP_START_PATTERNS = [
    r'(?:baby|infant)?\s*(?:went to |is in )?(?:sleep|bed|nap)(?:ing)?\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:put|putting)(?:ting)?\s+(?:baby|infant|him|her)?\s+(?:to|in)\s+(?:sleep|bed|nap)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:baby|infant)?\s*(?:is|started)\s+(?:sleeping|napping)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

SLEEP_END_PATTERNS = [
    r'(?:baby|infant)?\s*(?:woke|awake|wake|woken|got up)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:baby|infant)?\s*(?:is|has been)\s+(?:awake|up)\s+(?:since\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:baby|infant)?\s*(?:stopped|finished)\s+(?:sleeping|napping)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # Adding simpler patterns that are more likely to match
    r'(?:woke up|awoke)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:baby|infant)?\s*woke\s+(?:up\s+)?(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

FEED_START_PATTERNS = [
    r'(?:baby|infant)?\s*(?:is|started)\s+(?:feeding|eating|nursing|breastfeeding|bottle feeding)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:feeding|nursing|breastfeeding|bottle feeding)\s+(?:baby|infant)?\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:started|began)\s+(?:to feed|feeding|nursing|breastfeeding|bottle feeding)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:fed|feeding)\s+(?:baby|infant)?\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

FEED_END_PATTERNS = [
    r'(?:baby|infant)?\s*(?:finished|stopped|done|ended)\s+(?:feeding|eating|nursing|breastfeeding|bottle feeding)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:feeding|nursing|breastfeeding|bottle feeding)\s+(?:finished|stopped|ended|completed)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:finished|stopped|ended|completed)\s+(?:feeding|nursing|breastfeeding|bottle feeding)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

SUMMARY_PATTERNS = [
    r'(?:show|give|get|display)\s+(?:me\s+)?(?:a\s+)?(?:summary|report|overview|stats|statistics|data)\s+(?:of\s+)?(?:today|the day|this week|the week|this month|the month)',
    r'(?:what|how)\s+(?:is|was|were)\s+(?:the\s+)?(?:baby|infant)?\s*(?:routine|sleep|feeding|events)\s+(?:today|this week|this month)',
    r'(?:summary|report|overview|stats|statistics|data)\s+(?:of\s+)?(?:today|the day|this week|the week|this month|the month)',
    r'(?:today|day|week|month)(?:\'s)?\s+(?:summary|report|overview|stats|statistics|data)'
]

HELP_PATTERNS = [
    r'(?:how|help|explain|tell me how)\s+(?:to\s+)?(?:track|log|record)\s+(?:baby|infant)?\s*(?:routine|sleep|feeding|events)',
    r'(?:what|which)\s+(?:commands|tracking commands|routine commands)\s+(?:can I use|are available|do you support)',
    r'help\s+(?:with\s+)?(?:tracking|commands|routine)'
]

# Command patterns - Hebrew
SLEEP_START_PATTERNS_HE = [
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:הלך ל|נמצא ב|הלך לישון ב|ישן ב)?(?:שינה|מיטה|תנומה)(?:ישן)?\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:שם|שמתי)(?:ה)?\s+(?:תינוק|ילד|אותו|אותה|את התינוק)?\s+(?:ל|ב)\s+(?:שינה|מיטה|תנומה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:התחיל)\s+(?:לישון|לנמנם)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:התינוק|הילד)?\s*(?:נרדם|ישן|הלך לישון)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # Simpler patterns
    r'(?:שינה|לישון)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:התינוק|הילד)?\s*(?:הלך לישון)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

SLEEP_END_PATTERNS_HE = [
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:התעורר|ער|קם)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:הוא|היא)?\s*(?:ער|ערה)\s+(?:מ-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:הפסיק|סיים)\s+(?:לישון|לנמנם)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # Simpler patterns
    r'(?:התעורר|התעוררה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:קם|קמה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

FEED_START_PATTERNS_HE = [
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:אוכל|התחיל לאכול|מתחיל לאכול|אכל)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:האכלה|הנקה|בקבוק)\s+(?:תינוק|ילד|התינוק|הילד)?\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:התחלתי|התחיל|התחילה)\s+(?:להאכיל|להניק|לתת בקבוק)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:האכלתי|מאכיל|מאכילה)\s+(?:תינוק|ילד|התינוק|הילד|אותו|אותה)?\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

FEED_END_PATTERNS_HE = [
    r'(?:תינוק|ילד|התינוק|הילד)?\s*(?:סיים|הפסיק|גמר)\s+(?:לאכול|לינוק|את הבקבוק)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:האכלה|הנקה|בקבוק)\s+(?:הסתיימה|נגמרה|הסתיים|נגמר)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:סיימתי|סיים|סיימה|הפסקתי|הפסיק|הפסיקה)\s+(?:להאכיל|להניק|את הבקבוק)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)'
]

SUMMARY_PATTERNS_HE = [
    r'(?:הראה|הצג|תן|תראה)\s+(?:לי\s+)?(?:סיכום|דוח|סקירה|נתונים|סטטיסטיקה)\s+(?:של\s+)?(?:היום|השבוע|החודש)',
    r'(?:מה|איך)\s+(?:היה|היו|היתה)\s+(?:ה)?(?:שגרה|שינה|האכלה|אירועים)\s+(?:של\s+)?(?:התינוק|הילד)?\s*(?:היום|השבוע|החודש)',
    r'(?:סיכום|דוח|סקירה|נתונים|סטטיסטיקה)\s+(?:של\s+)?(?:היום|השבוע|החודש)',
    r'(?:היום|השבוע|החודש)(?:\'ה)?\s+(?:סיכום|דוח|סקירה|נתונים|סטטיסטיקה)',
    r'סיכום\s+(?:יום|שבוע|חודש)',
    r'^סיכום יום$',
    r'^סיכום שבוע$',
    r'^סיכום חודש$'
]

HELP_PATTERNS_HE = [
    r'(?:איך|עזרה|הסבר|תסביר לי איך)\s+(?:ל)?(?:עקוב|לרשום|לתעד)\s+(?:תינוק|ילד|התינוק|הילד)?\s*(?:שגרה|שינה|האכלה|אירועים)',
    r'(?:מה|איזה)\s+(?:פקודות|פקודות מעקב|פקודות שגרה)\s+(?:אני יכול להשתמש|זמינות|אתה תומך)',
    r'עזרה\s+(?:עם\s+)?(?:מעקב|פקודות|שגרה)'
]

def parse_time(time_str: str) -> Optional[datetime]:
    """
    Parse a time string into a datetime object
    
    Args:
        time_str: String representation of time
        
    Returns:
        Datetime object or None if parsing fails
    """
    try:
        # Clean up the time string
        time_str = time_str.strip().lower()
        
        # Handle AM/PM format
        is_pm = False
        if 'pm' in time_str or 'p.m.' in time_str:
            is_pm = True
            time_str = time_str.replace('pm', '').replace('p.m.', '').strip()
        elif 'am' in time_str or 'a.m.' in time_str:
            time_str = time_str.replace('am', '').replace('a.m.', '').strip()
        
        # Parse hours and minutes
        if ':' in time_str:
            hours, minutes = map(int, time_str.split(':'))
        else:
            hours = int(time_str)
            minutes = 0
        
        # Adjust for PM if needed
        if is_pm and hours < 12:
            hours += 12
        
        # Create datetime object for today with the specified time
        now = datetime.now()
        result = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        return result
    except Exception as e:
        logger.error(f"Error parsing time '{time_str}': {str(e)}")
        return None

def extract_notes(message: str, command: Dict[str, Any]) -> Optional[str]:
    """
    Extract additional notes from the message
    
    Args:
        message: The original message
        command: The detected command
        
    Returns:
        Extracted notes or None
    """
    # Remove the command part from the message
    if 'original_text' in command:
        remaining = message.replace(command['original_text'], '', 1).strip()
        
        # Check if there's anything meaningful left
        if len(remaining) > 3:  # Arbitrary threshold to avoid single characters
            return remaining
    
    return None

def detect_command(message: str) -> Optional[Dict[str, Any]]:
    """
    Detect if a message contains a tracking command
    
    Args:
        message: The user message to check
        
    Returns:
        A dictionary with command details or None if no command detected
    """
    # Convert message to lowercase for case-insensitive matching
    message_lower = message.lower()
    
    logger.info(f"Detecting command in message: '{message_lower}'")
    
    # Detect language (simple heuristic - can be improved)
    is_hebrew = bool(re.search(r'[\u0590-\u05FF]', message))
    logger.info(f"Message language detected as {'Hebrew' if is_hebrew else 'English'}")
    
    # Select appropriate patterns based on language
    if is_hebrew:
        sleep_start_patterns = SLEEP_START_PATTERNS_HE
        sleep_end_patterns = SLEEP_END_PATTERNS_HE
        feed_start_patterns = FEED_START_PATTERNS_HE
        feed_end_patterns = FEED_END_PATTERNS_HE
        summary_patterns = SUMMARY_PATTERNS_HE
        help_patterns = HELP_PATTERNS_HE
        language = "he"
    else:
        sleep_start_patterns = SLEEP_START_PATTERNS
        sleep_end_patterns = SLEEP_END_PATTERNS
        feed_start_patterns = FEED_START_PATTERNS
        feed_end_patterns = FEED_END_PATTERNS
        summary_patterns = SUMMARY_PATTERNS
        help_patterns = HELP_PATTERNS
        language = "en"
    
    # First check if it's a summary request to avoid misinterpreting as an event
    for pattern in summary_patterns:
        match = re.search(pattern, message_lower)
        if match:
            logger.info(f"Detected summary command: '{message_lower}'")
            
            # Determine period from the message
            period = "day"  # Default to day
            
            # Check for specific period indicators in Hebrew
            if is_hebrew:
                if "שבוע" in message_lower:
                    period = "week"
                elif "חודש" in message_lower:
                    period = "month"
                # The default is already "day" for "יום" or no specific period
            else:
                if "week" in message_lower:
                    period = "week"
                elif "month" in message_lower:
                    period = "month"
                # The default is already "day" for "today" or no specific period
            
            return {
                "command_type": "summary",
                "period": period,
                "language": language
            }
    
    # Check for help command
    for pattern in help_patterns:
        if re.search(pattern, message_lower):
            logger.info(f"Detected help command: '{message_lower}'")
            return {
                "command_type": "help",
                "language": language
            }
    
    # Check for sleep start command
    for pattern in sleep_start_patterns:
        match = re.search(pattern, message_lower)
        if match:
            time_str = match.group(1)
            parsed_time = parse_time(time_str)
            if parsed_time:
                logger.info(f"Detected sleep start command: '{match.group(0)}' with time {parsed_time}")
                return {
                    "command_type": "event",
                    "event_type": "sleep",
                    "action": "start",
                    "time": parsed_time,
                    "original_text": match.group(0),
                    "language": language
                }
    
    # Check for sleep end command
    for i, pattern in enumerate(sleep_end_patterns):
        match = re.search(pattern, message_lower)
        if match:
            time_str = match.group(1)
            parsed_time = parse_time(time_str)
            if parsed_time:
                logger.info(f"Detected sleep end command: '{match.group(0)}' with time {parsed_time} (pattern {i})")
                return {
                    "command_type": "event",
                    "event_type": "sleep",
                    "action": "end",
                    "time": parsed_time,
                    "original_text": match.group(0),
                    "language": language
                }
    
    # Check for feed start command
    for pattern in feed_start_patterns:
        match = re.search(pattern, message_lower)
        if match:
            time_str = match.group(1)
            parsed_time = parse_time(time_str)
            if parsed_time:
                logger.info(f"Detected feed start command: '{match.group(0)}' with time {parsed_time}")
                return {
                    "command_type": "event",
                    "event_type": "feed",
                    "action": "start",
                    "time": parsed_time,
                    "original_text": match.group(0),
                    "language": language
                }
    
    # Check for feed end command
    for pattern in feed_end_patterns:
        match = re.search(pattern, message_lower)
        if match:
            time_str = match.group(1)
            parsed_time = parse_time(time_str)
            if parsed_time:
                logger.info(f"Detected feed end command: '{match.group(0)}' with time {parsed_time}")
                return {
                    "command_type": "event",
                    "event_type": "feed",
                    "action": "end",
                    "time": parsed_time,
                    "original_text": match.group(0),
                    "language": language
                }
    
    logger.info("No command detected in message")
    return None

def get_help_text(language="en") -> str:
    """
    Get the help text for tracking commands
    
    Args:
        language: Language code (e.g., 'en', 'he')
        
    Returns:
        Formatted help text explaining available commands
    """
    if language == "he":
        return """
**פקודות מעקב שגרת תינוק**

אתה יכול לעקוב אחר שגרת התינוק שלך באמצעות פקודות בשפה טבעית. הנה כמה דוגמאות:

**מעקב שינה:**
- "התינוק הלך לישון ב-8:30 בערב"
- "שמתי אותו במיטה ב-7 בערב"
- "היא מנמנמת ב-2:30 אחה"צ"
- "התינוק התעורר ב-6 בבוקר"
- "הוא ער מאז 5:30 בבוקר"

**מעקב האכלה:**
- "התחלתי להאכיל ב-9 בבוקר"
- "האכלתי את התינוק ב-3 אחה"צ"
- "סיימתי הנקה ב-9:30 בבוקר"
- "סיימתי האכלה ב-4:15 אחה"צ"

**דוחות סיכום:**
- "הראה לי סיכום של היום"
- "קבל סיכום שבועי"
- "סיכום לחודש זה"

אתה יכול גם להוסיף הערות על ידי הוספת מידע נוסף אחרי הפקודה, כמו:
"התינוק הלך לישון ב-8 בערב אחרי אמבטיה חמה וסיפור"

כדי לראות את טקסט העזרה הזה שוב, פשוט הקלד "עזרה מעקב" או "איך לעקוב אחר שגרת תינוק".
"""
    else:  # Default to English
        return """
**Baby Routine Tracking Commands**

You can track your baby's routine using natural language commands. Here are some examples:

**Sleep Tracking:**
- "Baby went to sleep at 8:30pm"
- "Put him to bed at 7pm"
- "She's napping at 2:30pm"
- "Baby woke up at 6am"
- "He's been awake since 5:30am"

**Feeding Tracking:**
- "Started feeding at 9am"
- "Fed baby at 3pm"
- "Finished breastfeeding at 9:30am"
- "Done feeding at 4:15pm"

**Summary Reports:**
- "Show me today's summary"
- "Get weekly summary"
- "Summary for this month"

You can also add notes by including additional information after the command, like:
"Baby went to sleep at 8pm after a warm bath and story time"

To see this help text again, just type "help tracking" or "how to track baby routine".
"""

def format_summary_response(summary: Dict[str, Any]) -> str:
    """
    Format a summary dictionary into a readable response
    
    Args:
        summary: The summary dictionary from generate_summary()
        
    Returns:
        Formatted summary text
    """
    # Get language from summary if available, default to English
    language = summary.get("language", "en")
    
    if "error" in summary:
        if language == "he":
            return f"מצטער, לא הצלחתי ליצור סיכום: {summary['error']}"
        else:
            return f"Sorry, I couldn't generate a summary: {summary['error']}"
    
    period = summary["period"]
    start_date = summary["start_date"].strftime("%A, %B %d")
    
    # Format sleep summary
    sleep_data = summary["sleep"]
    sleep_count = sleep_data["total_events"]
    sleep_total = sleep_data["total_duration_minutes"]
    sleep_avg = sleep_data["average_duration_minutes"]
    
    # Format feed summary
    feed_data = summary["feed"]
    feed_count = feed_data["total_events"]
    feed_total = feed_data["total_duration_minutes"]
    feed_avg = feed_data["average_duration_minutes"]
    
    # Build the response based on language
    if language == "he":
        # Hebrew response
        if period == "day":
            period_name = "היום"
        elif period == "week":
            period_name = "השבוע"
        else:
            period_name = "החודש"
            
        response = f"**סיכום שגרת תינוק ל{period_name}** (מאז {start_date})\n\n"
        
        # Sleep section
        response += "**שינה:**\n"
        if sleep_count > 0:
            hours, minutes = divmod(int(sleep_total), 60)
            response += f"- סך הכל מפגשי שינה: {sleep_count}\n"
            response += f"- זמן שינה כולל: {hours}ש {minutes}ד\n"
            if sleep_avg > 0:
                avg_hours, avg_minutes = divmod(int(sleep_avg), 60)
                if avg_hours > 0:
                    response += f"- משך שינה ממוצע: {avg_hours}ש {avg_minutes}ד\n"
                else:
                    response += f"- משך שינה ממוצע: {avg_minutes}ד\n"
            
            # List recent sleep events (limit to 5)
            if sleep_data["events"]:
                response += "\nמפגשי שינה אחרונים:\n"
                # Sort events by start time to ensure most recent are shown
                sorted_events = sorted(sleep_data["events"], key=lambda x: x["start_time"])
                for event in sorted_events[-5:]:
                    start_time = event["start_time"].strftime("%I:%M %p")
                    if event["end_time"]:
                        end_time = event["end_time"].strftime("%I:%M %p")
                        duration_mins = event["duration_minutes"]
                        hours, mins = divmod(int(duration_mins), 60)
                        if hours > 0:
                            duration = f"{hours}ש {mins}ד"
                        else:
                            duration = f"{mins}ד"
                        response += f"- {start_time} עד {end_time} ({duration})\n"
                    else:
                        response += f"- התחיל ב-{start_time} (ממשיך)\n"
        else:
            response += "- לא נרשמו מפגשי שינה לתקופה זו.\n"
        
        # Feed section
        response += "\n**האכלה:**\n"
        if feed_count > 0:
            response += f"- סך הכל מפגשי האכלה: {feed_count}\n"
            if feed_total > 0:
                hours, minutes = divmod(int(feed_total), 60)
                if hours > 0:
                    response += f"- זמן האכלה כולל: {hours}ש {minutes}ד\n"
                else:
                    response += f"- זמן האכלה כולל: {minutes}ד\n"
            if feed_avg > 0:
                avg_minutes = int(feed_avg)
                response += f"- משך האכלה ממוצע: {avg_minutes}ד\n"
            
            # List recent feeding events (limit to 5)
            if feed_data["events"]:
                response += "\nמפגשי האכלה אחרונים:\n"
                # Sort events by start time to ensure most recent are shown
                sorted_events = sorted(feed_data["events"], key=lambda x: x["start_time"])
                for event in sorted_events[-5:]:
                    start_time = event["start_time"].strftime("%I:%M %p")
                    if event["end_time"]:
                        end_time = event["end_time"].strftime("%I:%M %p")
                        duration_mins = event["duration_minutes"]
                        response += f"- {start_time} עד {end_time} ({int(duration_mins)}ד)\n"
                    else:
                        response += f"- התחיל ב-{start_time} (ממשיך)\n"
        else:
            response += "- לא נרשמו מפגשי האכלה לתקופה זו.\n"
    else:
        # English response (original implementation)
        response = f"**Baby Routine Summary for {period}** (since {start_date})\n\n"
        
        # Sleep section
        response += "**Sleep:**\n"
        if sleep_count > 0:
            hours, minutes = divmod(int(sleep_total), 60)
            response += f"- Total sleep sessions: {sleep_count}\n"
            response += f"- Total sleep time: {hours}h {minutes}m\n"
            if sleep_avg > 0:
                avg_hours, avg_minutes = divmod(int(sleep_avg), 60)
                if avg_hours > 0:
                    response += f"- Average sleep duration: {avg_hours}h {avg_minutes}m\n"
                else:
                    response += f"- Average sleep duration: {avg_minutes}m\n"
            
            # List recent sleep events (limit to 5)
            if sleep_data["events"]:
                response += "\nRecent sleep sessions:\n"
                for event in sleep_data["events"][-5:]:
                    start_time = event["start_time"].strftime("%I:%M %p")
                    if event["end_time"]:
                        end_time = event["end_time"].strftime("%I:%M %p")
                        duration_mins = event["duration_minutes"]
                        hours, mins = divmod(int(duration_mins), 60)
                        if hours > 0:
                            duration = f"{hours}h {mins}m"
                        else:
                            duration = f"{mins}m"
                        response += f"- {start_time} to {end_time} ({duration})\n"
                    else:
                        response += f"- Started at {start_time} (ongoing)\n"
        else:
            response += "- No sleep sessions recorded for this period.\n"
        
        # Feed section
        response += "\n**Feeding:**\n"
        if feed_count > 0:
            response += f"- Total feeding sessions: {feed_count}\n"
            if feed_total > 0:
                hours, minutes = divmod(int(feed_total), 60)
                if hours > 0:
                    response += f"- Total feeding time: {hours}h {minutes}m\n"
                else:
                    response += f"- Total feeding time: {minutes}m\n"
            if feed_avg > 0:
                avg_minutes = int(feed_avg)
                response += f"- Average feeding duration: {avg_minutes}m\n"
            
            # List recent feeding events (limit to 5)
            if feed_data["events"]:
                response += "\nRecent feeding sessions:\n"
                for event in feed_data["events"][-5:]:
                    start_time = event["start_time"].strftime("%I:%M %p")
                    if event["end_time"]:
                        end_time = event["end_time"].strftime("%I:%M %p")
                        duration_mins = event["duration_minutes"]
                        response += f"- {start_time} to {end_time} ({int(duration_mins)}m)\n"
                    else:
                        response += f"- Started at {start_time} (ongoing)\n"
        else:
            response += "- No feeding sessions recorded for this period.\n"
    
    return response 