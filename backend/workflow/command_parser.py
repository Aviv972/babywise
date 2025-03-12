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
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:הלך ל|הלכה ל|נמצא ב|נמצאת ב|הלך לישון ב|הלכה לישון ב|ישן ב|ישנה ב)?(?:שינה|מיטה|תנומה)(?:ישן|ישנה)?\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:שם|שמתי)(?:ה)?\s+(?:תינוק|תינוקת|ילד|ילדה|אותו|אותה|את התינוק|את התינוקת)?\s+(?:ל|ב)\s+(?:שינה|מיטה|תנומה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:התחיל|התחילה)\s+(?:לישון|לנמנם)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:התינוק|התינוקת|הילד|הילדה)?\s*(?:נרדם|נרדמה|ישן|ישנה|הלך לישון|הלכה לישון)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # Simpler patterns
    r'(?:שינה|לישון)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:התינוק|התינוקת|הילד|הילדה)?\s*(?:הלך לישון|הלכה לישון)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # Specific patterns for "נרדמה ב13" format
    r'(?:נרדם|נרדמה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|תינוקת|התינוק|התינוקת)\s+(?:נרדם|נרדמה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # More flexible pattern to catch with or without the "ב" prefix
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:נרדם|נרדמה)\s+(?:ב)?(\d{1,2})(?:\:(\d{2}))?'
]

SLEEP_END_PATTERNS_HE = [
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:התעורר|התעוררה|ער|ערה|קם|קמה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:הוא|היא)?\s*(?:ער|ערה)\s+(?:מ-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:הפסיק|הפסיקה|סיים|סיימה)\s+(?:לישון|לנמנם)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # Simpler patterns
    r'(?:התעורר|התעוררה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:קם|קמה)\s+(?:ב-?\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}(?::\d{2})?)',
    # More flexible pattern to catch with or without the "ב" prefix
    r'(?:תינוק|תינוקת|ילד|ילדה|התינוק|התינוקת|הילד|הילדה)?\s*(?:התעורר|התעוררה)\s+(?:ב)?(\d{1,2})(?:\:(\d{2}))?'
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
    r'סיכום\s+(?:יום|שבוע|חודש)'
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
        logger.info(f"Parsing time from string: '{time_str}'")
        
        # Clean up the time string
        time_str = time_str.strip().lower()
        
        # Handle AM/PM format
        is_pm = False
        if 'pm' in time_str or 'p.m.' in time_str:
            is_pm = True
            time_str = time_str.replace('pm', '').replace('p.m.', '').strip()
        elif 'am' in time_str or 'a.m.' in time_str:
            time_str = time_str.replace('am', '').replace('a.m.', '').strip()
        
        # Handle Hebrew time indicators
        if 'בבוקר' in time_str:
            time_str = time_str.replace('בבוקר', '').strip()
        elif 'בערב' in time_str or 'בלילה' in time_str:
            is_pm = True
            time_str = time_str.replace('בערב', '').replace('בלילה', '').strip()
        elif 'בצהריים' in time_str:
            is_pm = True
            time_str = time_str.replace('בצהריים', '').strip()
        
        # Parse hours and minutes
        if ':' in time_str:
            hours, minutes = map(int, time_str.split(':'))
        else:
            # Just a simple number like "13"
            try:
                hours = int(time_str)
                minutes = 0
                logger.info(f"Parsed simple hour format: hours={hours}, minutes={minutes}")
            except ValueError:
                logger.warning(f"Could not parse '{time_str}' as a simple hour")
                return None
        
        # Adjust for PM if needed
        if is_pm and hours < 12:
            hours += 12
            logger.info(f"Adjusted for PM: hours={hours}")
        
        # If hours is greater than 12, assume 24-hour format
        if hours > 12 and hours <= 23:
            logger.info(f"Assuming 24-hour format for hour {hours}")
        elif hours > 23:
            logger.warning(f"Invalid hour value: {hours}")
            return None
        
        # Create datetime object for today with the specified time
        now = datetime.now()
        result = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        logger.info(f"Successfully parsed time: {result.strftime('%Y-%m-%d %H:%M')}")
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
        if re.search(pattern, message_lower):
            logger.info(f"Detected summary command: '{message_lower}'")
            return {
                "command_type": "summary",
                "period": "day",  # Default to day, can be refined
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
                    "event_type": "feeding",
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
                    "event_type": "feeding",
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
    # Handle both string and datetime objects for start_date
    if isinstance(summary["start_date"], str):
        try:
            # Try to parse the string as a datetime
            start_date_obj = datetime.fromisoformat(summary["start_date"])
            start_date = start_date_obj.strftime("%A, %B %d")
        except ValueError:
            # If parsing fails, use the string as is
            start_date = summary["start_date"]
    else:
        # If it's already a datetime object
        start_date = summary["start_date"].strftime("%A, %B %d")
    
    # Get routines data
    routines = summary.get("routines", {})
    
    # Format sleep summary
    sleep_data = routines.get("sleep", {})
    sleep_count = sleep_data.get("total_events", 0)
    
    # Convert hours to minutes for consistency
    sleep_total_hours = sleep_data.get("total_duration", 0)
    sleep_total = sleep_total_hours * 60  # Convert hours to minutes
    
    sleep_avg_hours = sleep_data.get("average_duration", 0)
    sleep_avg = sleep_avg_hours * 60  # Convert hours to minutes
    
    # Format feed summary - use "feeding" instead of "feed" to match database
    feed_data = routines.get("feeding", {})
    feed_count = feed_data.get("total_events", 0)
    
    # Convert hours to minutes for consistency
    feed_total_hours = feed_data.get("total_duration", 0)
    feed_total = feed_total_hours * 60  # Convert hours to minutes
    
    feed_avg_hours = feed_data.get("average_duration", 0)
    feed_avg = feed_avg_hours * 60  # Convert hours to minutes
    
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
            
            # Show latest sleep event if available
            latest_event = sleep_data.get("latest_event")
            if latest_event:
                response += "\nמפגש שינה אחרון:\n"
                start_time_str = latest_event["start_time"]
                if isinstance(start_time_str, str):
                    try:
                        start_time = datetime.fromisoformat(start_time_str).strftime("%I:%M %p")
                    except ValueError:
                        # Handle potential format issues
                        start_time = start_time_str
                else:
                    start_time = start_time_str.strftime("%I:%M %p")
                
                end_time_str = latest_event.get("end_time")
                if end_time_str:
                    if isinstance(end_time_str, str):
                        try:
                            end_time = datetime.fromisoformat(end_time_str).strftime("%I:%M %p")
                        except ValueError:
                            # Handle potential format issues
                            end_time = end_time_str
                    else:
                        end_time = end_time_str.strftime("%I:%M %p")
                    
                    # Calculate duration
                    if isinstance(start_time_str, str) and isinstance(end_time_str, str):
                        try:
                            start_dt = datetime.fromisoformat(start_time_str)
                            end_dt = datetime.fromisoformat(end_time_str)
                            duration_mins = (end_dt - start_dt).total_seconds() / 60
                        except ValueError:
                            # If parsing fails, use the total duration from summary
                            duration_mins = sleep_total
                    else:
                        if isinstance(start_time_str, datetime) and isinstance(end_time_str, datetime):
                            duration_mins = (end_time_str - start_time_str).total_seconds() / 60
                        else:
                            duration_mins = sleep_total
                    
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
        
        # Feed section - use "feeding" instead of "feed"
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
            
            # Show latest feed event if available
            latest_event = feed_data.get("latest_event")
            if latest_event:
                response += "\nמפגש האכלה אחרון:\n"
                start_time_str = latest_event["start_time"]
                if isinstance(start_time_str, str):
                    try:
                        start_time = datetime.fromisoformat(start_time_str).strftime("%I:%M %p")
                    except ValueError:
                        start_time = start_time_str
                else:
                    start_time = start_time_str.strftime("%I:%M %p")
                
                end_time_str = latest_event.get("end_time")
                if end_time_str:
                    if isinstance(end_time_str, str):
                        try:
                            end_time = datetime.fromisoformat(end_time_str).strftime("%I:%M %p")
                        except ValueError:
                            end_time = end_time_str
                    else:
                        end_time = end_time_str.strftime("%I:%M %p")
                    
                    # Calculate duration
                    if isinstance(start_time_str, str) and isinstance(end_time_str, str):
                        try:
                            start_dt = datetime.fromisoformat(start_time_str)
                            end_dt = datetime.fromisoformat(end_time_str)
                            duration_mins = (end_dt - start_dt).total_seconds() / 60
                        except ValueError:
                            duration_mins = feed_total
                    else:
                        if isinstance(start_time_str, datetime) and isinstance(end_time_str, datetime):
                            duration_mins = (end_time_str - start_time_str).total_seconds() / 60
                        else:
                            duration_mins = feed_total
                    
                    hours, mins = divmod(int(duration_mins), 60)
                    if hours > 0:
                        duration = f"{hours}ש {mins}ד"
                    else:
                        duration = f"{mins}ד"
                    response += f"- {start_time} עד {end_time} ({duration})\n"
                else:
                    response += f"- התחיל ב-{start_time} (ממשיך)\n"
        else:
            response += "- לא נרשמו מפגשי האכלה לתקופה זו.\n"
    else:
        # English response
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
            
            # Show latest sleep event if available
            latest_event = sleep_data.get("latest_event")
            if latest_event:
                response += "\nLatest sleep session:\n"
                start_time_str = latest_event["start_time"]
                if isinstance(start_time_str, str):
                    try:
                        start_time = datetime.fromisoformat(start_time_str).strftime("%I:%M %p")
                    except ValueError:
                        start_time = start_time_str
                else:
                    start_time = start_time_str.strftime("%I:%M %p")
                
                end_time_str = latest_event.get("end_time")
                if end_time_str:
                    if isinstance(end_time_str, str):
                        try:
                            end_time = datetime.fromisoformat(end_time_str).strftime("%I:%M %p")
                        except ValueError:
                            end_time = end_time_str
                    else:
                        end_time = end_time_str.strftime("%I:%M %p")
                    
                    # Calculate duration
                    if isinstance(start_time_str, str) and isinstance(end_time_str, str):
                        try:
                            start_dt = datetime.fromisoformat(start_time_str)
                            end_dt = datetime.fromisoformat(end_time_str)
                            duration_mins = (end_dt - start_dt).total_seconds() / 60
                        except ValueError:
                            duration_mins = sleep_total
                    else:
                        if isinstance(start_time_str, datetime) and isinstance(end_time_str, datetime):
                            duration_mins = (end_time_str - start_time_str).total_seconds() / 60
                        else:
                            duration_mins = sleep_total
                    
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
        
        # Feed section - use "feeding" instead of "feed"
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
            
            # Show latest feed event if available
            latest_event = feed_data.get("latest_event")
            if latest_event:
                response += "\nLatest feeding session:\n"
                start_time_str = latest_event["start_time"]
                if isinstance(start_time_str, str):
                    try:
                        start_time = datetime.fromisoformat(start_time_str).strftime("%I:%M %p")
                    except ValueError:
                        start_time = start_time_str
                else:
                    start_time = start_time_str.strftime("%I:%M %p")
                
                end_time_str = latest_event.get("end_time")
                if end_time_str:
                    if isinstance(end_time_str, str):
                        try:
                            end_time = datetime.fromisoformat(end_time_str).strftime("%I:%M %p")
                        except ValueError:
                            end_time = end_time_str
                    else:
                        end_time = end_time_str.strftime("%I:%M %p")
                    
                    # Calculate duration
                    if isinstance(start_time_str, str) and isinstance(end_time_str, str):
                        try:
                            start_dt = datetime.fromisoformat(start_time_str)
                            end_dt = datetime.fromisoformat(end_time_str)
                            duration_mins = (end_dt - start_dt).total_seconds() / 60
                        except ValueError:
                            duration_mins = feed_total
                    else:
                        if isinstance(start_time_str, datetime) and isinstance(end_time_str, datetime):
                            duration_mins = (end_time_str - start_time_str).total_seconds() / 60
                        else:
                            duration_mins = feed_total
                    
                    hours, mins = divmod(int(duration_mins), 60)
                    if hours > 0:
                        duration = f"{hours}h {mins}m"
                    else:
                        duration = f"{mins}m"
                    response += f"- {start_time} to {end_time} ({duration})\n"
                else:
                    response += f"- Started at {start_time} (ongoing)\n"
        else:
            response += "- No feeding sessions recorded for this period.\n"
    return response 