"""
Babywise Chatbot - Response Generation

This module implements the response generation workflow node for the Babywise Chatbot.
It generates responses based on the conversation history, selected domain, and context.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Set
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
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

def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
   """Generate a response based on the conversation history and domain"""
   try:
       logger.info("Starting generate_response function")
       messages = state["messages"]
       logger.info(f"Messages count: {len(messages)}")
       domain = state["domain"]
       logger.info(f"Domain: {domain}")
       context = state["context"]
       logger.info(f"Context: {json.dumps(context, default=str)}")
       language = state.get("language", "en")
       logger.info(f"Language: {language}")
      
       # Get the domain-specific prompt
       domain_prompt = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])
       logger.info(f"Using domain prompt for: {domain}")
      
       # Format context for inclusion in the prompt
       context_str = json.dumps(context, default=str)
      
       # Add language-specific instructions
       language_instruction = LANGUAGE_INSTRUCTIONS.get(language, "")
       logger.info(f"Added language instructions for: {language}")
      
       # Add gender-specific instructions for Hebrew
       if language == "he":
           # Check if we have gender context
           gender_instruction = ""
           user_context = state.get("user_context", {})
           is_female_context = user_context.get("is_female_context", False)
           is_breastfeeding_context = user_context.get("is_breastfeeding_context", False)
           is_maternal_context = user_context.get("is_maternal_context", False)
           
           logger.info(f"Hebrew gender context - female: {is_female_context}, breastfeeding: {is_breastfeeding_context}, maternal: {is_maternal_context}")
          
           if is_female_context:
               gender_instruction = """
IMPORTANT: This is a female user. Use feminine forms in Hebrew:
- Address the user as 'את' (not 'אתה')
- Use feminine verb forms (e.g., 'את צריכה' not 'אתה צריך')
- Use feminine possessive forms (e.g., 'שלך' with feminine conjugation)
- Use feminine adjectives when referring to the user
"""
               if is_breastfeeding_context:
                   gender_instruction += """
This is specifically about breastfeeding. Use appropriate feminine terminology:
- 'כשאת מניקה' (when you breastfeed)
- 'חלב האם שלך' (your breast milk)
- 'השד שלך' (your breast)
"""
               if is_maternal_context:
                   gender_instruction += """
This is about maternal/pregnancy topics. Use appropriate feminine terminology:
- 'ההיריון שלך' (your pregnancy)
- 'הלידה שלך' (your delivery)
- 'הגוף שלך' (your body)
"""
          
           language_instruction += """
          
For Hebrew responses, please follow these additional guidelines:
1. Use proper Hebrew grammar and syntax - avoid direct translations from English.
2. Ensure correct use of gender forms (masculine/feminine) in verbs and adjectives.
  - For breastfeeding, pregnancy, or postpartum topics, ALWAYS use feminine forms (את, שלך, etc.)
  - For general parenting topics, use feminine forms by default unless context clearly indicates a male user
  - Use gender-appropriate verb conjugations (e.g., "את צריכה" not "אתה צריך" for female users)
3. Use natural Hebrew phrasing rather than literal translations.
4. Maintain right-to-left text flow and proper punctuation.
5. Use appropriate Hebrew terminology for baby care concepts.
6. Verify that your response reads naturally to a native Hebrew speaker.
7. Address the user directly in second person (את/אתה) rather than using impersonal forms.
"""
          
           # Add the gender-specific instruction if applicable
           if gender_instruction:
               language_instruction += gender_instruction
               logger.info("Added gender-specific instructions for Hebrew")
      
       # Add additional instructions based on domain
       additional_instructions = ""
       logger.info("Adding domain-specific additional instructions")
      
       if domain == "health_safety":
           # Check if critical information is missing for health-related queries
           missing_info = []
          
           # For health conditions, check if baby age is available (critical for health advice)
           health_conditions = []
           if "health_conditions" in context and "value" in context["health_conditions"]:
               health_conditions = context["health_conditions"]["value"]
               
           if health_conditions and "baby_age" not in context:
               missing_info.append("baby's age")
          
           # For fever specifically, check if temperature details are available
           if health_conditions and "fever" in health_conditions:
               # Check if temperature was mentioned in any message
               temp_mentioned = False
               for msg in messages:
                   if msg.type == "human" and re.search(r'(\d+(?:\.\d+)?)[°\s]?[CF]', msg.content):
                       temp_mentioned = True
                       break
              
               if not temp_mentioned:
                   missing_info.append("temperature reading")
          
           if missing_info:
               additional_instructions = f"\nIMPORTANT: The user has not provided the following critical information: {', '.join(missing_info)}. "
               additional_instructions += "Consider asking for this information if it's essential for providing accurate advice, but only if you don't have enough context to give a helpful general response."
               logger.info(f"Added missing health info prompt: {missing_info}")
      
       elif domain == "sleep":
           # Check if baby age is available (critical for sleep advice)
           if "baby_age" not in context:
               additional_instructions = "\nIMPORTANT: The user has not provided the baby's age, which is often critical for providing appropriate sleep advice. "
               additional_instructions += "Consider asking for this information if it's essential for your response, but only if you don't have enough context to give a helpful general response."
               logger.info("Added missing baby age prompt for sleep domain")
      
       elif domain == "feeding":
           # Check if baby age is available (critical for feeding advice)
           if "baby_age" not in context:
               additional_instructions = "\nIMPORTANT: The user has not provided the baby's age, which is essential for providing appropriate feeding advice. "
               additional_instructions += "Consider asking for this information if it's essential for your response, but only if you don't have enough context to give a helpful general response."
               logger.info("Added missing baby age prompt for feeding domain")
      
       elif domain == "baby_gear":
           # Check if budget information is available
           missing_info = []
           if "budget" not in context:
               missing_info.append("budget or price range")
          
           if "baby_age" not in context:
               missing_info.append("baby's age")
          
           if missing_info:
               additional_instructions = f"\nIMPORTANT: The user has not provided the following information that may be helpful: {', '.join(missing_info)}. "
               additional_instructions += "Consider asking for this information if it's essential for providing specific product recommendations, but only if you don't have enough context to give a helpful general response."
               logger.info(f"Added missing baby gear info prompt: {missing_info}")
      
       elif domain == "development":
           # Check if baby age is available (critical for development advice)
           if "baby_age" not in context:
               additional_instructions = "\nIMPORTANT: The user has not provided the baby's age, which is essential for providing appropriate developmental guidance. "
               additional_instructions += "Consider asking for this information if it's essential for your response, but only if you don't have enough context to give a helpful general response."
               logger.info("Added missing baby age prompt for development domain")
      
       # Create prompt template
       logger.info("Creating prompt template")
       
       # Escape any curly braces in the context string to prevent template errors
       safe_context_str = context_str.replace("{", "{{").replace("}", "}}")
       
       prompt = ChatPromptTemplate.from_messages([
           ("system", domain_prompt + language_instruction + additional_instructions),
           MessagesPlaceholder(variable_name="messages"),
           ("system", f"Current context: {safe_context_str}")
       ])
      
       # Generate response with adjusted temperature setting for non-English languages
       # Lower temperature for non-English languages to improve accuracy
       temperature = 0.3 if language != "en" else 0.5
       logger.info(f"Creating ChatOpenAI model with temperature: {temperature}")
       try:
           # Ensure API key is loaded
           import os
           from dotenv import load_dotenv
           import pathlib
           
           # Try to load API key directly if not already in environment
           if 'OPENAI_API_KEY' not in os.environ or not os.environ['OPENAI_API_KEY']:
               # Try multiple possible locations for the .env file
               possible_paths = [
                   pathlib.Path(__file__).parents[3] / '.env',  # Original path
                   pathlib.Path(__file__).parents[2] / '.env',  # One level up
                   pathlib.Path.cwd() / '.env',                 # Current working directory
               ]
               
               for dotenv_path in possible_paths:
                   logger.info(f"Attempting to load API key from: {dotenv_path}")
                   if dotenv_path.exists():
                       logger.info(f"Found .env file at: {dotenv_path}")
                       load_dotenv(dotenv_path=dotenv_path, override=True)
                       if 'OPENAI_API_KEY' in os.environ and os.environ['OPENAI_API_KEY']:
                           logger.info(f"Successfully loaded OpenAI API key from .env file: {os.environ['OPENAI_API_KEY'][:10]}...")
                           break
           
           # Double check API key is available
           if 'OPENAI_API_KEY' in os.environ and os.environ['OPENAI_API_KEY']:
               logger.info(f"OpenAI API key found in environment variables: {os.environ['OPENAI_API_KEY'][:10]}...")
               
               # Create the model with explicit API key
               model = ChatOpenAI(
                   model="gpt-4o-mini", 
                   temperature=temperature,
                   openai_api_key=os.environ['OPENAI_API_KEY']
               )
               logger.info("Creating chain")
               chain = prompt | model
               logger.info("Invoking chain")
               response = chain.invoke({"messages": messages})
               logger.info("Chain invocation completed")
           else:
               logger.warning("OpenAI API key not found or empty in environment variables")
               raise ValueError("OpenAI API key not found or is empty")
       except Exception as e:
           logger.warning(f"Error creating or invoking OpenAI model: {str(e)}")
           logger.info("Using mock response instead")
           # Create a more detailed mock response based on the domain
           mock_content = create_detailed_mock_response(domain, context, language)
           response = AIMessage(content=mock_content)
       
       # Add response to messages
       state["messages"].append(response)
       logger.info("Added response to messages")
      
       logger.info(f"Generated response for domain: {domain}")
       logger.info(f"State summary - Domain: {domain}, Messages: {len(state['messages'])}, Context: {json.dumps(context, default=str)}")
      
       return state
      
   except Exception as e:
       logger.error(f"Error generating response: {str(e)}", exc_info=True)
       logger.error(f"Error type: {type(e).__name__}")
       logger.error(f"Error args: {e.args}")
       # Add a fallback response
       error_message = "I'm sorry, I encountered an error. Could you please try again?"
      
       # Translate error message based on language
       if language == "es":
           error_message = "Lo siento, encontré un error. ¿Podrías intentarlo de nuevo?"
       elif language == "fr":
           error_message = "Je suis désolé, j'ai rencontré une erreur. Pourriez-vous réessayer?"
       elif language == "de":
           error_message = "Es tut mir leid, ich bin auf einen Fehler gestoßen. Könnten Sie es bitte noch einmal versuchen?"
       elif language == "he":
           error_message = "אני מצטער, נתקלתי בשגיאה. האם תוכל לנסות שוב?"
       elif language == "ar":
           error_message = "أنا آسف، لقد واجهت خطأ. هل يمكنك المحاولة مرة أخرى؟"
      
       # Add error message to messages
       state["messages"].append(AIMessage(content=error_message))
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