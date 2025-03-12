"""
Babywise Chatbot - Response Generation

This module implements the response generation workflow node for the Babywise Chatbot.
It generates responses based on the conversation history, selected domain, and context.
"""

import re
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional, Set
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from backend.models.message_types import AIMessage, HumanMessage
from backend.workflow.domain_prompts import DOMAIN_PROMPTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language-specific instructions
LANGUAGE_INSTRUCTIONS = {
    "en": """
Respond in English. Use clear, concise language appropriate for parents of young children.
""",
    "he": """
Respond in Hebrew (עברית). Use natural, conversational Hebrew that would be understood by Israeli parents.
Make sure to use proper Hebrew grammar, syntax, and vocabulary.

IMPORTANT TRANSLATION GUIDELINES:
1. DO NOT translate English idioms or expressions literally. Use equivalent Hebrew expressions instead.
2. Avoid direct word-for-word translations that might sound unnatural or inappropriate in Hebrew.
3. Be careful with medical terms - use the proper Hebrew medical terminology.
4. For baby care advice, use terms that Israeli parents would naturally use.
5. Pay special attention to verb conjugations and gender agreement in Hebrew.
6. When describing actions or techniques, ensure they make sense culturally in an Israeli context.
7. NEVER use Google Translate-style literal translations of English phrases.

EXAMPLES OF PROBLEMATIC TRANSLATIONS TO AVOID:
- "Babies die for X" (English idiom meaning "babies love X") should NEVER be translated as "תינוקות מתים על X" - instead use "תינוקות אוהבים מאוד X" or "תינוקות נהנים מאוד מ-X"
- "Tummy time" should be translated as "זמן שכיבה על הבטן" not a literal word-by-word translation
- "Burping the baby" should be translated as "הוצאת גיהוקים לתינוק" or "לגרום לתינוק לגהק" not a literal translation
""",
    "ar": """
Respond in Arabic (العربية). Use natural, conversational Arabic that would be understood by Arabic-speaking parents.
Make sure to use proper Arabic grammar, syntax, and vocabulary.
"""
}

def add_messages(messages, state):
    """Add messages to the state"""
    if "messages" not in state:
        state["messages"] = []
    state["messages"].extend(messages)
    return state

async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a response to the user's message
    
    Args:
        state: The current conversation state
        
    Returns:
        The updated state
    """
    try:
        start_time = time.time()
        logger.info("Starting generate_response function")
        
        # Ensure chat history exists
        messages = state.get("messages", [])
        logger.info(f"Messages count: {len(messages)}")
        
        # Get domain from state
        domain = state.get("domain", "general")
        language = state.get("language", "en")
        
        # Get context from state
        context = state.get("context", {})
        user_context = state.get("user_context", {})
        
        # Log the context information we have
        logger.info(f"Generating response with domain: {domain}")
        logger.info(f"Language: {language}")
        logger.info(f"Context: {json.dumps(context, default=str)}")
        logger.info(f"User context: {json.dumps(user_context, default=str)}")
        
        # Prepare conversation history for LLM
        history = []
        
        # Include up to 10 most recent messages
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            history.append({"role": role, "content": msg.content})
        
        # Check for context references before generating response
        latest_message = messages[-1].content.lower() if messages else ""
        age_query = False
        
        # Detect if the user is asking about the baby's age in any language
        age_queries_en = ["how old", "what age", "what is the age"]
        age_queries_he = ["בת כמה", "בן כמה", "מה הגיל"]
        
        if language == "en" and any(q in latest_message.lower() for q in age_queries_en):
            age_query = True
        elif language == "he" and any(q in latest_message for q in age_queries_he):
            age_query = True
            
        # Add context-aware system message
        system_message = {}
        
        # If the user is asking about age and we have that information, specifically include it
        if age_query and ("baby_age" in context or "baby_age" in user_context):
            if "baby_age" in context:
                age_value = context["baby_age"]["value"]
                age_unit = context["baby_age"]["unit"]
            else:
                age_value = user_context.get("baby_age")
                age_unit = user_context.get("baby_age_unit", "months")
                
            if language == "en":
                system_message = {
                    "role": "system",
                    "content": f"You are Babywise, a helpful assistant that provides information about baby care. The user's baby is {age_value} {age_unit} old. Make sure to reference this age when answering age-related questions."
                }
            else:  # Hebrew
                system_message = {
                    "role": "system",
                    "content": f"אתה Babywise, עוזר מועיל שמספק מידע על טיפול בתינוקות. התינוק של המשתמש הוא בן/בת {age_value} {age_unit}. הקפד להתייחס לגיל זה בתשובות לשאלות הקשורות לגיל."
                }
        else:
            # Create domain-specific system prompt
            if domain == "sleep":
                if language == "en":
                    system_content = "You are Babywise, a helpful assistant specializing in baby sleep advice."
                else:  # Hebrew
                    system_content = "אתה Babywise, עוזר מועיל המתמחה בייעוץ שינה לתינוקות."
            elif domain == "feeding":
                if language == "en":
                    system_content = "You are Babywise, a helpful assistant specializing in baby feeding advice."
                else:  # Hebrew
                    system_content = "אתה Babywise, עוזר מועיל המתמחה בייעוץ האכלה לתינוקות."
            elif domain == "baby_gear":
                if language == "en":
                    system_content = "You are Babywise, a helpful assistant specializing in baby gear recommendations."
                else:  # Hebrew
                    system_content = "אתה Babywise, עוזר מועיל המתמחה בהמלצות לציוד תינוקות."
            elif domain == "health":
                if language == "en":
                    system_content = "You are Babywise, a helpful assistant providing general information about baby health. You are not a doctor and do not provide medical advice."
                else:  # Hebrew
                    system_content = "אתה Babywise, עוזר מועיל המספק מידע כללי על בריאות תינוקות. אתה לא רופא ואינך מספק ייעוץ רפואי."
            elif domain == "development":
                if language == "en":
                    system_content = "You are Babywise, a helpful assistant specializing in baby development milestones and activities."
                else:  # Hebrew
                    system_content = "אתה Babywise, עוזר מועיל המתמחה באבני דרך בהתפתחות תינוקות ופעילויות."
            else:  # general domain
                if language == "en":
                    system_content = "You are Babywise, a helpful assistant that provides information about baby care."
                else:  # Hebrew
                    system_content = "אתה Babywise, עוזר מועיל המספק מידע על טיפול בתינוקות."
            
            # Add any context we have
            if context and "baby_age" in context:
                age_value = context["baby_age"]["value"]
                age_unit = context["baby_age"]["unit"]
                
                if language == "en":
                    system_content += f" The user's baby is {age_value} {age_unit} old."
                else:  # Hebrew
                    system_content += f" התינוק של המשתמש הוא בן/בת {age_value} {age_unit}."
            
            system_message = {
                "role": "system",
                "content": system_content
            }
        
        # Build messages for the API call
        messages_for_api = [system_message] + history
        
        # Generate response
        response_content = await generate_llm_response(messages_for_api, language)
        logger.info(f"LLM response received (first 100 chars): {response_content[:100]}")
        
        # Add to message history
        state["messages"].append(AIMessage(content=response_content))
        
        # Track completion time
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Response generated in {duration:.2f} seconds")
        
        return state
    except Exception as e:
        logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
        # Return fallback response in case of error
        if messages:
            fail_message = "I apologize, but I encountered an error generating a response. Could you please try again?"
            if state.get("language") == "he":
                fail_message = "אני מתנצל, אך נתקלתי בשגיאה בעת יצירת תשובה. אנא נסה שוב."
            state["messages"].append(AIMessage(content=fail_message))
        return state

def create_mock_response(state: Dict[str, Any], domain: str, language: str) -> Dict[str, Any]:
    """Create a mock response when LLM is not available"""
    last_user_message = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1].content
    
    # Create a simple mock response based on the user's message
    if "sleep" in last_user_message.lower() or "נרדם" in last_user_message or "ישן" in last_user_message:
        if language == "he":
            response = "לתינוקות בגילאים שונים יש צרכי שינה שונים. תינוקות בני 0-3 חודשים צריכים בדרך כלל 14-17 שעות שינה ביממה, בעוד שתינוקות בני 4-11 חודשים צריכים 12-15 שעות. האם תוכל לספר לי עוד על התינוק שלך ועל דפוסי השינה שלו?"
        else:
            response = "Babies at different ages have different sleep needs. Newborns (0-3 months) typically need 14-17 hours of sleep per day, while infants (4-11 months) need about 12-15 hours. Can you tell me more about your baby and their sleep patterns?"
    
    elif "feed" in last_user_message.lower() or "eat" in last_user_message.lower() or "אוכל" in last_user_message or "האכל" in last_user_message:
        if language == "he":
            response = "האכלת תינוקות משתנה עם הגיל. תינוקות עד גיל 6 חודשים צריכים חלב אם או תחליף חלב בלבד. לאחר גיל 6 חודשים, אפשר להתחיל להוסיף מזון מוצק. האם תוכל לספר לי עוד על התינוק שלך ועל האכלתו?"
        else:
            response = "Feeding babies changes with age. Babies under 6 months need only breast milk or formula. After 6 months, you can start introducing solid foods. Can you tell me more about your baby and their feeding habits?"
    
    elif "diaper" in last_user_message.lower() or "חיתול" in last_user_message:
        if language == "he":
            response = "החלפת חיתולים היא חלק חשוב בטיפול בתינוק. תינוקות צעירים צריכים החלפת חיתול כל 2-3 שעות. האם יש לך שאלות ספציפיות לגבי החלפת חיתולים?"
        else:
            response = "Diaper changing is an important part of baby care. Young babies need a diaper change every 2-3 hours. Do you have specific questions about diaper changing?"
    
    else:
        # General response
        if language == "he":
            response = "אני כאן כדי לעזור לך בכל שאלה הקשורה לטיפול בתינוק, כולל שינה, האכלה, התפתחות ועוד. במה אוכל לעזור לך היום?"
        else:
            response = "I'm here to help with any baby care questions, including sleep, feeding, development, and more. How can I assist you today?"
    
    # Add the response to the state
    state["messages"].append(AIMessage(content=response))
    logger.info(f"Generated mock response: '{response}'")
    
    return state

def create_detailed_mock_response(domain, context, language="en"):
    """Create a detailed mock response based on domain and context."""
    if domain == "feeding" and "baby_age" in context:
        age = context["baby_age"]["value"]
        unit = context["baby_age"]["unit"]
        if age <= 3 and unit == "months":
            return (
                f"For a {age} {unit} old baby, the primary nutrition should be breast milk or formula. "
                f"At this age, babies typically feed 8-12 times per day (every 2-3 hours). "
                f"Each feeding session might last about 20-40 minutes if breastfeeding, or take about 15-20 minutes if formula feeding. "
                f"Your baby should be consuming approximately 2-3 ounces of formula per feeding. "
                f"It's important to watch for hunger cues like rooting, putting hands to mouth, and increased alertness."
            )
        elif 4 <= age <= 6 and unit == "months":
            return (
                f"At {age} {unit}, your baby should still primarily consume breast milk or formula. "
                f"However, this is also when many pediatricians recommend introducing solid foods. "
                f"Start with single-ingredient purees like rice cereal mixed with breast milk or formula, "
                f"then gradually introduce pureed fruits and vegetables. "
                f"Continue with 4-6 breast milk or formula feedings daily, with 1-2 small solid food sessions."
            )
        else:
            return (
                f"For a {age} {unit} old baby, feeding typically involves a combination of breast milk or formula "
                f"and age-appropriate solid foods. The specific recommendations vary based on developmental stage. "
                f"Would you like more specific guidance for this age?"
            )
    
    elif domain == "sleep" and "baby_age" in context:
        age = context["baby_age"]["value"]
        unit = context["baby_age"]["unit"]
        if age <= 3 and unit == "months":
            return (
                f"At {age} {unit}, babies typically sleep 14-17 hours in a 24-hour period. "
                f"This is usually broken into 3-5 naps during the day and longer stretches at night. "
                f"Many babies this age still wake up 2-4 times at night for feeding. "
                f"Newborns don't yet have established circadian rhythms, so their sleep patterns may seem random. "
                f"Always place your baby on their back to sleep, on a firm surface without pillows, blankets, or toys."
            )
        elif 4 <= age <= 6 and unit == "months":
            return (
                f"At {age} {unit}, your baby likely needs about 12-15 hours of sleep per day. "
                f"This typically includes 2-3 naps during the day (totaling 3-4 hours) and about 10-11 hours at night. "
                f"Many babies this age are developing more regular sleep patterns and may be able to sleep for longer stretches at night. "
                f"Some babies might be ready for sleep training at this age if they're still waking frequently."
            )
        else:
            return (
                f"For a {age} {unit} old baby, sleep needs and patterns vary based on developmental stage. "
                f"Generally, younger babies need more total sleep and more frequent naps. "
                f"As they grow, they gradually consolidate sleep into longer nighttime periods and fewer daytime naps. "
                f"Would you like more specific guidance for this age?"
            )
    
    elif domain == "development" and "baby_age" in context:
        age = context["baby_age"]["value"]
        unit = context["baby_age"]["unit"]
        if age <= 3 and unit == "months":
            return (
                f"At {age} {unit}, your baby is developing rapidly! Typical milestones include: "
                f"Beginning to lift their head during tummy time, "
                f"Following objects with their eyes, "
                f"Responding to loud sounds, "
                f"Starting to smile socially, "
                f"Bringing hands to face and mouth, "
                f"And beginning to make cooing sounds. "
                f"Remember that development varies among babies, and these are just general guidelines."
            )
        elif 4 <= age <= 6 and unit == "months":
            return (
                f"At {age} {unit}, exciting developments are happening! Your baby may be: "
                f"Rolling over in both directions, "
                f"Beginning to sit with support, "
                f"Reaching for and grasping objects, "
                f"Laughing and making consonant sounds, "
                f"Recognizing familiar faces, "
                f"And showing interest in food when others are eating. "
                f"These milestones vary among babies, so don't worry if your little one isn't doing all of these yet."
            )
        else:
            return (
                f"At {age} {unit}, babies are typically developing various physical, cognitive, and social skills. "
                f"Development is highly individual, with each baby progressing at their own pace. "
                f"Would you like more specific information about typical milestones for this age?"
            )
    
    else:
        return (
            "I can provide information about baby care topics including feeding, sleep, development, and general care. "
            "For more personalized advice, please share your baby's age and specific concerns or questions you have. "
            "I'm here to support you through your parenting journey with evidence-based information."
        ) 

async def generate_llm_response(messages: List[Dict[str, str]], language: str = "en") -> str:
    """
    Generate a response using the OpenAI API
    
    Args:
        messages: List of message dictionaries with role and content
        language: Language code for the response
        
    Returns:
        The generated response text
    """
    try:
        # Check if OpenAI API key is available
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        # If key starts with ${, it's not properly set
        if not openai_api_key or openai_api_key.startswith("${"):
            logger.warning("OpenAI API key not found or invalid, using mock response")
            # Return a mock response based on language
            if language == "he":
                return "אני כאן לעזור לך בכל שאלה לגבי טיפול בתינוק, כולל שינה, האכלה, התפתחות ועוד. איך אוכל לעזור לך היום?"
            else:
                return "I'm here to help with any baby care questions, including sleep, feeding, development, and more. How can I assist you today?"
        
        logger.info(f"OpenAI API key available: {bool(openai_api_key)}")
        
        # Initialize the LLM
        logger.info("Initializing ChatOpenAI with model: gpt-4o-mini")
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.4,
            openai_api_key=openai_api_key
        )
        
        # Log information about the request
        logger.info(f"Sending request to OpenAI with {len(messages)} messages")
        
        # Make the API call
        try:
            result = await llm.ainvoke(messages)
            response = result.content
            logger.info(f"OpenAI response received (first 100 chars): {response[:100]}")
            return response
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            logger.info("Trying fallback model: gpt-3.5-turbo")
            
            try:
                # Try with fallback model
                fallback_llm = ChatOpenAI(
                    model="gpt-3.5-turbo", 
                    temperature=0.4,
                    openai_api_key=openai_api_key
                )
                
                result = await fallback_llm.ainvoke(messages)
                response = result.content
                logger.info(f"Fallback model response received (first 100 chars): {response[:100]}")
                return response
            except Exception as fallback_error:
                logger.error(f"Error with fallback model: {str(fallback_error)}")
                
                # Return a fallback response based on language
                if language == "he":
                    return "אני מתנצל, אך נתקלתי בבעיה בחיבור לשירות. האם תוכל לנסות את השאלה שלך שוב מאוחר יותר?"
                else:
                    return "I apologize, but I'm experiencing connection issues with my service. Could you try your question again later?"
    
    except Exception as e:
        logger.error(f"Unexpected error in generate_llm_response: {str(e)}", exc_info=True)
        
        # Return a generic error response based on language
        if language == "he":
            return "אני מתנצל, אך נתקלתי בשגיאה בלתי צפויה. האם תוכל לנסח את השאלה שלך בצורה אחרת?"
        else:
            return "I apologize, but I encountered an unexpected error. Could you please rephrase your question?" 