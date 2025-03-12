"""
Babywise Chatbot - Response Generation

This module implements the response generation workflow node for the Babywise Chatbot.
It generates responses based on the conversation history, selected domain, and context.
"""

import re
import json
import logging
import os
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
    """Generate a response using the LLM."""
    try:
        # Extract user messages
        user_messages = [msg for msg in state.get("messages", []) if isinstance(msg, HumanMessage)]
        if not user_messages:
            logger.warning("No user messages found in state")
            return state
        
        last_user_message = user_messages[-1].content
        logger.info(f"Last user message: '{last_user_message}'")
        
        # Get basic context
        domain = state.get("domain", "general")
        language = state.get("language", state.get("metadata", {}).get("language", "en"))
        context = state.get("context", {})
        logger.info(f"Domain: {domain}, Language: {language}")
        
        # Check if OpenAI API key is available
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        # If key starts with ${, it's not properly set
        if not openai_api_key or openai_api_key.startswith("${"):
            logger.warning("OpenAI API key not found or invalid, using mock response")
            return create_mock_response(state, domain, language)
            
        logger.info(f"OpenAI API key available: {bool(openai_api_key)}")
        
        try:
            # Initialize the LLM
            logger.info("Initializing ChatOpenAI with model: gpt-4o-mini")
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.4,
                openai_api_key=openai_api_key
            )
            
            # Get the domain-specific prompt
            domain_prompt = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])
            
            # Get language-specific instructions
            lang_instructions = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
            
            # Create the prompt template
            logger.info("Creating prompt template")
            system_prompt = f"""
You are the Babywise Assistant, a specialized AI assistant for new and expecting parents.

{domain_prompt}

{lang_instructions}

Current context:
{json.dumps(context, indent=2)}
            """
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
            ])
            
            # Extract chat history
            chat_history = []
            for message in state["messages"]:
                if isinstance(message, HumanMessage):
                    chat_history.append(("human", message.content))
                elif isinstance(message, AIMessage):
                    chat_history.append(("ai", message.content))
            
            logger.info(f"Preparing to invoke LLM with {len(chat_history)} messages in history")
            
            # Prepare the formatted chat history outside the try block
            formatted_chat_history = [{"role": role, "content": content} for role, content in chat_history]
            logger.info(f"Formatted chat history with {len(formatted_chat_history)} messages")
            
            # Invoke the LLM
            try:
                logger.info("Invoking LLM")
                # Test with a basic Hello World first to validate API call
                test_result = await llm.ainvoke([{"role": "user", "content": "Say Hello World"}])
                logger.info(f"Test LLM call successful: {test_result.content[:50]}...")
                
                # Create the actual payload
                chain = prompt | llm
                logger.info(f"Sending actual request to LLM with {len(formatted_chat_history)} messages")
                
                # Log a sample of the input to help with debugging
                sample_input = {"chat_history": formatted_chat_history[:2]} if formatted_chat_history else {"chat_history": []}
                logger.info(f"Sample of chain input: {json.dumps(sample_input, indent=2)[:200]}...")
                
                result = await chain.ainvoke({"chat_history": formatted_chat_history})
                response = result.content
                logger.info(f"LLM response received (first 100 chars): {response[:100]}")
            except Exception as llm_error:
                logger.error(f"Error during LLM invocation: {str(llm_error)}", exc_info=True)
                # Try a fallback model
                try:
                    logger.info("Trying fallback model: gpt-3.5-turbo")
                    fallback_llm = ChatOpenAI(
                        model="gpt-3.5-turbo", 
                        temperature=0.4,
                        openai_api_key=openai_api_key
                    )
                    chain = prompt | fallback_llm
                    # Use the formatted_chat_history from above
                    result = await chain.ainvoke({"chat_history": formatted_chat_history})
                    response = result.content
                    logger.info(f"Fallback LLM response received (first 100 chars): {response[:100]}")
                except Exception as fallback_error:
                    logger.error(f"Error during fallback LLM invocation: {str(fallback_error)}", exc_info=True)
                    logger.error("Both primary and fallback models failed, using mock response")
                    return create_mock_response(state, domain, language)
            
            # Add the response to the messages
            state["messages"].append(AIMessage(content=response))
            return state
        
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            return create_mock_response(state, domain, language)
            
    except Exception as e:
        logger.error(f"Unexpected error in generate_response: {str(e)}", exc_info=True)
        # Add a default response in case of error
        mock_response = "I'm here to help with any baby care questions, including sleep, feeding, development, and more. How can I assist you today?"
        state["messages"].append(AIMessage(content=mock_response))
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