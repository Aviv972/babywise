"""
Babywise Chatbot - Domain Selection

This module implements the domain selection workflow node for the Babywise Chatbot.
It selects the most appropriate domain (sleep, feeding, etc.) based on the content
of the latest message and the conversation context.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from backend.models.message_types import HumanMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def select_domain(state: Dict[str, Any]) -> Dict[str, Any]:
   """Select the appropriate domain based on the latest message"""
   try:
       messages = state["messages"]
       context = state["context"]
       
       # Ensure context is a dictionary
       if not isinstance(context, dict):
           context = {}
           state["context"] = context
      
       # If no messages, return general domain
       if not messages:
           state["domain"] = "general"
           return state
      
       # Get the latest message
       latest_msg = None
       for msg in reversed(messages):
           if msg.type == "human":
               latest_msg = msg
               break
               
       if not latest_msg:
           state["domain"] = "general"
           return state
      
       content = latest_msg.content.lower()
      
       # Check for health and safety concerns first (highest priority)
       health_keywords = [
           # English
            'fever', 'sick', 'temperature', 'rash', 'vomit', 'throw up', 'throwing up',
            'diarrhea', 'constipation', 'poop', 'stool', 'bowel', 'cough', 'cold', 'flu',
            'vaccine', 'vaccination', 'shot', 'immunization', 'medicine', 'medication',
            'doctor', 'pediatrician', 'hospital', 'emergency', 'injury', 'hurt', 'pain',
            'crying', 'cry', 'inconsolable', "won't stop crying", 'ear', 'eye', 'nose',
            'throat', 'breathing', 'breath', 'choking', 'choke', 'allergy', 'allergic',
            'reaction', 'swelling', 'infection', 'virus', 'bacteria', 'antibiotic',
            'teething', 'teeth', 'tooth', 'gum', 'drool', 'drooling',
            # Hebrew
            'חום', 'חולה', 'טמפרטורה', 'פריחה', 'הקאה', 'להקיא', 'בהקאה',
            'שלשול', 'עצירות', 'צואה', 'צואה', 'מעיים', 'שיעול', 'הצטננות', 'שפעת',
            'חיסון', 'חיסון', 'זריקה', 'חיסון', 'תרופה', 'תרופה',
            'רופא', 'רופא ילדים', 'בית חולים', 'חירום', 'פציעה', 'פצוע', 'כאב',
            'בכי', 'לבכות', 'בלתי מנחם', 'לא מפסיק לבכות', 'אוזן', 'עין', 'אף',
            'גרון', 'נשימה', 'נשימה', 'חניקה', 'להיחנק', 'אלרגיה', 'אלרגי',
            'תגובה', 'נפיחות', 'זיהום', 'וירוס', 'חיידקים', 'אנטיביוטיקה',
            'יצאת שיניים', 'שיניים', 'שן', 'חניכיים', 'רוק', 'נזילת רוק' 
       ]
      
       safety_keywords = [
           # English
            'safety', 'safe', 'danger', 'dangerous', 'accident', 'emergency',
            'childproof', 'baby proof', 'babyproof', 'child proof', 'hazard',
            'fall', 'falling', 'choke', 'choking', 'drown', 'drowning', 'burn',
            'burning', 'poison', 'poisoning', 'injury', 'hurt', 'car seat',
            'carseat', 'stroller', 'carrier', 'baby carrier', 'crib', 'bassinet',
            'playpen', 'play pen', 'gate', 'baby gate', 'lock', 'cabinet lock',
            'outlet', 'plug', 'cord', 'blind cord', 'window', 'stairs', 'stair',
            'bath', 'bathtub', 'tub', 'water', 'pool', 'supervision', 'supervise',
            'monitor', 'watching', 'watch',
            # Hebrew
            'בטיחות', 'בטוח', 'סכנה', 'מסוכן', 'תאונה', 'חירום',
            'מאובטח לילדים', 'הגנה לתינוק', 'תינוק בטוח', 'הגנה לילדים', 'סיכון',
            'נפילה', 'נופל', 'חניקה', 'מחניק', 'טובע', 'טביעה', 'כווייה',
            'בוער', 'רעל', 'הרעלה', 'פציעה', 'פצוע', 'מושב רכב',
            'מושב רכב', 'עגלת תינוק', 'מנשא', 'מנשא לתינוק', 'מיטת תינוק', 'סל תינוק',
            'גדר לתינוק', 'גדר לתינוק', 'שער', 'שער בטיחות לתינוק', 'מנעול', 'מנעול ארון',
            'שקע', 'תקע', 'כבל', 'חבל וילון', 'חלון', 'מדרגות', 'מדרגה',
            'אמבטיה', 'אמבטיה', 'אמבטיה', 'מים', 'בריכה', 'השגחה', 'להשגיח',
            'מוניטור', 'צופה', 'צפה'
       ]
      
       # Check for health conditions in context
       has_health_condition = False
       if "health_conditions" in context and "value" in context["health_conditions"]:
           has_health_condition = len(context["health_conditions"]["value"]) > 0
      
       # Check for safety concerns in context
       has_safety_concern = False
       if "safety_concerns" in context and "value" in context["safety_concerns"]:
           has_safety_concern = len(context["safety_concerns"]["value"]) > 0
      
       # Check for health and safety keywords in the message
       if has_health_condition or has_safety_concern or any(keyword in content for keyword in health_keywords + safety_keywords):
           state["domain"] = "health_safety"
           return state
      
       # Check for sleep domain
       sleep_keywords = [
                'sleep', 'nap', 'bedtime', 'bed time', 'night', 'wake', 'waking',
            'woke', 'tired', 'drowsy', 'dream', 'dreaming', 'snore', 'snoring',
            'crib', 'bassinet', 'co-sleep', 'cosleep', 'co sleep', 'swaddle',
            'swaddling', 'night', 'midnight', 'evening', 'morning', 'routine',
            'schedule', 'pattern', 'habit', 'cry it out', 'crying it out',
            'ferber', 'sleep train', 'sleep training', 'pacifier', 'paci',
            'dummy', 'suck', 'sucking', 'white noise', 'sound machine',
            'night light', 'nightlight', 'dark', 'darkness', 'quiet', 'silence',
            'awake', 'asleep', 'doze', 'dozing', 'rest', 'resting', 'restless',
            'fussy', 'fussing', 'settle', 'settling', 'comfort', 'comfortable',
            'uncomfortable', 'position', 'back', 'side', 'tummy', 'stomach',
            # Hebrew
            'שינה', 'תנומה', 'שעת השינה', 'שעת השינה', 'לילה', 'להתעורר', 'מתעורר',
            'התעורר', 'עייף', 'מנמנם', 'חלום', 'חולם', 'הנחנח', 'מנחנח',
            'מיטת תינוק', 'סל תינוק', 'לישון יחד', 'לישון יחד', 'לישון יחד', 'לעטוף',
            'עטיפה', 'לילה', 'חצות', 'ערב', 'בוקר', 'שגרה',
            'לוח זמנים', 'תבנית', 'הרגל', 'השארת הילד לבכי', 'השארת הילד לבכי',
            'פרבר', 'שיטת השינה', 'אימון שינה', 'מוצץ', 'מוצץ',
            'מוצץ', 'למצוץ', 'מציצה', 'רעש לבן', 'מכשיר קול',
            'אור לילה', 'אור לילה', 'חשוך', 'חושך', 'שקט', 'שתיקה',
            'ער', 'ישן', 'לנמנם', 'נמנום', 'מנוחה', 'מנוחה', 'חסר מנוחה',
            'קיטקיט', 'קיטקיט', 'להרגיע', 'מתרגע', 'נחמה', 'נוח',
            'לא נוח', 'מיקום', 'גב', 'צד', 'בטן', 'קיבה'
       ]
      
       if any(keyword in content for keyword in sleep_keywords):
           state["domain"] = "sleep"
           return state
      
       # Check for feeding domain
       feeding_keywords = [
            'feed', 'feeding', 'eat', 'eating', 'food', 'formula', 'breast',
        'breastfeed', 'breastfeeding', 'breast feed', 'breast feeding',
        'nurse', 'nursing', 'bottle', 'bottles', 'bottlefeed', 'bottle feed',
        'bottlefeeding', 'bottle feeding', 'hungry', 'hunger', 'starving',
        'full', 'burp', 'burping', 'spit', 'spitting', 'spit up', 'spitting up',
        'vomit', 'vomiting', 'throw up', 'throwing up', 'reflux', 'gerd',
        'digest', 'digestion', 'digestive', 'stomach', 'tummy', 'belly',
        'gas', 'gassy', 'colic', 'colicky', 'milk', 'supply', 'pump', 'pumping',
        'latch', 'latching', 'nipple', 'pacifier', 'paci', 'dummy', 'suck',
        'sucking', 'swallow', 'swallowing', 'solids', 'puree', 'cereal',
        'vegetable', 'fruit', 'meat', 'protein', 'snack', 'meal', 'breakfast',
        'lunch', 'dinner', 'ounce', 'oz', 'milliliter', 'ml', 'cup', 'spoon',
        'fork', 'plate', 'bowl', 'bib', 'highchair', 'high chair',
        # Hebrew
        'להאכיל', 'האכלה', 'לאכול', 'אכילה', 'מזון', 'פורמולה', 'שד',
        'להניק', 'הנקה', 'הנקה', 'הנקה', 'להניק', 'הנקה', 'בקבוק', 'בקבוקים',
        'להאכיל בבקבוק', 'להאכיל בבקבוק', 'האכלה בבקבוק', 'להאכיל בבקבוק',
        'רעב', 'רעב', 'רעב מאוד', 'מלא', 'הגאה', 'הגהה', 'לירק', 'לירק',
        'הקאה קלה', 'הקאה קלה', 'הקאה', 'הקאה', 'להקיא', 'בהקאה', 'ריפלוקס', 'gerd',
        'לעכל', 'עיכול', 'עיכול', 'קיבה', 'בטן', 'בטן',
        'גז', 'מרגיש גזים', 'קוליק', 'קוליקי', 'חלב', 'אספקה', 'משאבה', 'משאבה',
        'אחיזה', 'אחיזה', 'פטמה', 'מוצץ', 'מוצץ', 'מוצץ', 'למצוץ', 'מציצה',
        'לבלוע', 'בליעה', 'מוצקים', 'פירה', 'דגנים',
        'ירק', 'פרי', 'בשר', 'חלבון', 'חטיף', 'ארוחה', 'ארוחת בוקר',
        'ארוחת צהריים', 'ארוחת ערב', 'אוז', 'אוז', 'מיליליטר', 'מ"ל', 'כוס',
        'כף', 'מזלג', 'צלחת', 'קערה', 'סינר', 'כיסא אוכל לתינוק', 'כיסא אוכל לתינוק'
       ]
      
       if any(keyword in content for keyword in feeding_keywords):
           state["domain"] = "feeding"
           return state
      
       # Check for baby gear domain
       gear_keywords = [
           'gear', 'equipment', 'product', 'item', 'buy', 'purchase', 'recommend',
           'recommendation', 'suggest', 'suggestion', 'review', 'best', 'top',
           'stroller', 'pram', 'buggy', 'car seat', 'carseat', 'carrier', 'wrap',
           'sling', 'bassinet', 'crib', 'cot', 'playpen', 'play pen', 'pack and play',
           'pack n play', 'swing', 'bouncer', 'rocker', 'monitor', 'baby monitor',
           'camera', 'diaper', 'nappy', 'wipe', 'changing table', 'changing pad',
           'bottle', 'pump', 'sterilizer', 'warmer', 'formula maker', 'high chair',
           'highchair', 'booster', 'seat', 'bath', 'bathtub', 'tub', 'towel',
           'washcloth', 'lotion', 'cream', 'ointment', 'oil', 'soap', 'shampoo',
           'thermometer', 'medicine', 'medication', 'toy', 'book', 'play', 'mat',
           'activity', 'mobile', 'music', 'sound', 'clothes', 'clothing', 'outfit',
           'onesie', 'sleeper', 'pajama', 'sock', 'hat', 'mitten', 'shoe', 'blanket',
           'swaddle', 'brand', 'store', 'shop', 'price', 'cost', 'expensive', 'cheap',
           'affordable', 'budget', 'worth', 'value', 'quality', 'durable', 'safe',
           'safety', 'recall', 'recalled'
       ]
      
       # Check for budget in context (strong indicator of baby gear domain)
       has_budget = "budget" in context
      
       if has_budget or any(keyword in content for keyword in gear_keywords):
           state["domain"] = "baby_gear"
           return state
      
       # Check for development domain
       development_keywords = [
            # English
            'gear', 'equipment', 'product', 'item', 'buy', 'purchase', 'recommend',
            'recommendation', 'suggest', 'suggestion', 'review', 'best', 'top',
            'stroller', 'pram', 'buggy', 'car seat', 'carseat', 'carrier', 'wrap',
            'sling', 'bassinet', 'crib', 'cot', 'playpen', 'play pen', 'pack and play',
            'pack n play', 'swing', 'bouncer', 'rocker', 'monitor', 'baby monitor',
            'camera', 'diaper', 'nappy', 'wipe', 'changing table', 'changing pad',
            'bottle', 'pump', 'sterilizer', 'warmer', 'formula maker', 'high chair',
            'highchair', 'booster', 'seat', 'bath', 'bathtub', 'tub', 'towel',
            'washcloth', 'lotion', 'cream', 'ointment', 'oil', 'soap', 'shampoo',
            'thermometer', 'medicine', 'medication', 'toy', 'book', 'play', 'mat',
            'activity', 'mobile', 'music', 'sound', 'clothes', 'clothing', 'outfit',
            'onesie', 'sleeper', 'pajama', 'sock', 'hat', 'mitten', 'shoe', 'blanket',
            'swaddle', 'brand', 'store', 'shop', 'price', 'cost', 'expensive', 'cheap',
            'affordable', 'budget', 'worth', 'value', 'quality', 'durable', 'safe',
            'safety', 'recall', 'recalled',
            # Hebrew
            'ציוד', 'ציוד', 'מוצר', 'פריט', 'לקנות', 'רכישה', 'להמליץ',
            'המלצה', 'להציע', 'הצעה', 'ביקורת', 'הכי טוב', 'טופ',
            'עגלת תינוק', 'עגלת תינוק', 'עגלת תינוק', 'מושב רכב', 'מושב רכב',
            'מנשא', 'עטיפה', 'סלינג', 'סל תינוק', 'מיטת תינוק', 'מיטת תינוק',
            'גדר לתינוק', 'גדר לתינוק', 'פאק אנד פליי', 'פאק אנד פליי',
            'נדנדה', 'נדנדה', 'נדנדה', 'מוניטור', 'מוניטור לתינוק',
            'מצלמה', 'חיתול', 'חיתול', 'מגבונים', 'שולחן החלפת חיתולים', 'מזרן החלפה',
            'בקבוק', 'משאבה', 'משחט', 'מחמם', 'מכונת פורמולה', 'כיסא אוכל לתינוק',
            'כיסא אוכל לתינוק', 'מושב מגדיל', 'מושב', 'אמבטיה', 'אמבטיה', 'אמבטיה',
            'מגבת', 'מטלית', 'קרם לחות', 'קרם', 'משחה', 'שמן', 'סבון',
            'שמפו', 'מדחום', 'תרופה', 'תרופה', 'צעצוע', 'ספר', 'משחק', 'מחצלת',
            'פעילות', 'מובייל', 'מוזיקה', 'צליל', 'בגדים', 'לבוש', 'תלבושת',
            'אונזי', 'חליפת שינה', 'פיג\'מה', 'גרב', 'כובע', 'כפפה', 'נעל', 'שמיכה',
            'עיטוף', 'מותג', 'חנות', 'חנות', 'מחיר', 'עלות', 'יקר', 'זול',
            'בר השגה', 'תקציב', 'שווי', 'ערך', 'איכות', 'עמיד', 'בטוח',
            'בטיחות', 'החזרה', 'שהוחזר'
       ]
      
       # Check for baby age in context (strong indicator of development domain)
       has_baby_age = "baby_age" in context
      
       if has_baby_age or any(keyword in content for keyword in development_keywords):
           state["domain"] = "development"
           return state
      
       # Default to general domain if no specific domain is detected
       state["domain"] = "general"
       return state
      
   except Exception as e:
       logger.error(f"Error selecting domain: {str(e)}", exc_info=True)
       # Default to general domain in case of error
       state["domain"] = "general"
       return state 