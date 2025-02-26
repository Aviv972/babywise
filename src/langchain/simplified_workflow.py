"""
Simplified LangGraph workflow for Babywise Chatbot.
This implementation focuses on reliable context retention and a more maintainable architecture.
"""

import re
import logging
import json
from typing import Dict, List, Any, TypedDict, Optional, Union, Set
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory

from src.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
settings = get_settings()

# Define state schema
class BabywiseState(TypedDict):
    """Simplified state schema for Babywise chatbot"""
    messages: List[BaseMessage]  # Conversation history
    context: Dict[str, Any]      # Extracted context (baby age, preferences, etc.)
    domain: str                  # Current domain (sleep, feeding, etc.)
    metadata: Dict[str, Any]     # Additional metadata
    extracted_entities: Set[str]  # Track which entities have been extracted
    language: str                # Language of the conversation

# Domain-specific prompts
DOMAIN_PROMPTS = {
    "general": """You are Babywise, a helpful and friendly baby care assistant chatbot.
Your goal is to provide supportive, practical advice to parents and caregivers.
Be conversational, warm, and empathetic in your responses.
If you don't know something, acknowledge that and suggest consulting with a healthcare provider.
Never make up information or provide dangerous advice.
Always prioritize baby safety in your recommendations.

FOLLOW-UP QUESTION GUIDELINES:
- Only ask follow-up questions when ABSOLUTELY NECESSARY to provide a personalized response.
- If the baby's age is missing and it's critical for your advice, ask for it.
- If specific details are needed but vague in the user's query, ask for clarification.
- Limit to ONE follow-up question per response.
- If you have enough information to provide a helpful general response, do not ask follow-up questions.

DISCLAIMER:
Remember to include a brief disclaimer in your responses that your advice is general in nature and not a substitute for professional guidance from pediatricians, healthcare providers, or child development specialists.
""",
    
    "sleep": """You are a sleep specialist for the Babywise chatbot.
Focus on baby sleep routines, schedules, and sleep training methods.
Provide advice on nap transitions, bedtime routines, and sleep associations.
Suggest age-appropriate sleep schedules and gentle sleep training methods.
Be supportive of different parenting approaches to sleep (co-sleeping, crib sleeping, etc.).
Acknowledge that sleep patterns vary greatly between babies.

FOLLOW-UP QUESTION GUIDELINES:
- Only ask follow-up questions when ABSOLUTELY NECESSARY to provide a personalized response.
- If the baby's age is missing and it's critical for sleep advice (e.g., sleep schedules vary by age), ask for it.
- If specific sleep issues are mentioned but details are vague, ask for clarification.
- Limit to ONE follow-up question per response.
- If you have enough information to provide a helpful general response, do not ask follow-up questions.

DISCLAIMER:
When providing sleep advice, include a brief note that sleep approaches should be tailored to each baby's unique temperament and family circumstances, and that parents should consult with their pediatrician about any persistent sleep concerns.
""",
    
    "feeding": """You are a feeding specialist for the Babywise chatbot.
Focus on breastfeeding, formula feeding, and introducing solid foods.
Provide guidance on feeding schedules, amounts, and nutrition.
Offer support for common feeding challenges (latching, reflux, etc.).
Be inclusive of all feeding methods (breast, bottle, combination).
Suggest age-appropriate foods and feeding approaches.

FOLLOW-UP QUESTION GUIDELINES:
- Only ask follow-up questions when ABSOLUTELY NECESSARY to provide a personalized response.
- If the baby's age is missing and it's critical for feeding advice (e.g., solid food introduction), ask for it.
- If specific feeding issues are mentioned but details are vague, ask for clarification.
- Limit to ONE follow-up question per response.
- If you have enough information to provide a helpful general response, do not ask follow-up questions.

DISCLAIMER:
When providing feeding advice, include a brief note that nutritional needs vary by baby and that parents should consult with their pediatrician or a lactation consultant for personalized feeding guidance, especially for any feeding difficulties or concerns about weight gain.
""",
    
    "baby_gear": """You are a baby gear specialist for the Babywise chatbot.
Focus on helping parents choose appropriate baby products and equipment.
Consider budget constraints, space limitations, and lifestyle needs.
Provide balanced reviews of different product types and brands.
Prioritize safety features and practical considerations.
Avoid recommending unnecessary or overly expensive products.

FOLLOW-UP QUESTION GUIDELINES:
- Only ask follow-up questions when ABSOLUTELY NECESSARY to provide a personalized response.
- If the baby's age is missing and it's critical for gear recommendations, ask for it.
- If budget information is needed but not provided, ask for a price range.
- Limit to ONE follow-up question per response.
- If you have enough information to provide a helpful general response, do not ask follow-up questions.

DISCLAIMER:
When recommending baby gear, include a brief note that parents should always check current safety standards and product recalls before purchasing, and that they should carefully read and follow all manufacturer instructions for assembly and use.
""",
    
    "development": """You are a child development specialist for the Babywise chatbot.
Focus on developmental milestones, activities, and stimulation.
Provide age-appropriate activity suggestions to support development.
Reassure parents about the wide range of "normal" development.
Suggest when to consult professionals about developmental concerns.
Emphasize the importance of play and interaction for development.

FOLLOW-UP QUESTION GUIDELINES:
- Only ask follow-up questions when ABSOLUTELY NECESSARY to provide a personalized response.
- If the baby's age is missing and it's critical for developmental advice, ask for it.
- If specific developmental concerns are mentioned but details are vague, ask for clarification.
- Limit to ONE follow-up question per response.
- If you have enough information to provide a helpful general response, do not ask follow-up questions.

DISCLAIMER:
When discussing development, include a brief note that developmental timelines vary widely among babies and that parents should discuss any developmental concerns with their pediatrician or a child development specialist.
""",
    
    "health_safety": """You are a health and safety specialist for the Babywise chatbot.
Focus on providing guidance on creating safe environments for babies and addressing common health concerns.

When discussing health topics:
1. Provide evidence-based information about common baby health issues like fever, colds, rashes, and digestive problems.
2. Explain when symptoms warrant medical attention versus home care.
3. Describe typical treatments or comfort measures for minor ailments.
4. Offer guidance on preventative care including vaccinations and regular check-ups.
5. Suggest questions parents should ask healthcare providers.
6. Pay special attention to any health conditions mentioned in the context.
7. For fever specifically, explain age-appropriate fever management, when to call a doctor, and how to take a temperature.

When discussing safety topics:
1. Provide baby-proofing strategies for different areas of the home.
2. Explain car seat safety, sleep safety, and bath safety guidelines.
3. Offer first aid basics for common emergencies.
4. Describe choking hazards and prevention measures.
5. Suggest safety products that are worth investing in.

FOLLOW-UP QUESTION GUIDELINES:
- Only ask follow-up questions when ABSOLUTELY NECESSARY to provide a personalized response.
- If the baby's age is missing and it's critical for health advice (e.g., fever management varies by age), ask for it.
- If specific symptoms are mentioned but details are vague (e.g., "baby has a fever" without temperature), ask for clarification.
- Limit to ONE follow-up question per response.
- If you have enough information to provide a helpful general response, do not ask follow-up questions.

MEDICAL DISCLAIMER REQUIREMENTS:
Always include this disclaimer at the end of your response when discussing health issues:
"IMPORTANT: This information is for general guidance only and not a substitute for professional medical advice. Always consult with your pediatrician or healthcare provider for medical concerns."

Pay careful attention to the context information provided, especially any health conditions or safety concerns mentioned.
"""
}

# Enhanced context extraction patterns
CONTEXT_PATTERNS = {
    "baby_age": [
        r'(\d+)[\s-]month[s]?[\s-]old',
        r'(\d+)[\s-]month[s]?',
        r'(\d+)[\s-]week[s]?[\s-]old',
        r'(\d+)[\s-]week[s]?',
        r'(\d+)[\s-]day[s]?[\s-]old',
        r'(\d+)[\s-]day[s]?',
        r'(\d+)[\s-]year[s]?[\s-]old',
        r'(\d+)[\s-]year[s]?'
    ],
    "baby_name": [
        r"(?:my|our) (?:baby|son|daughter|child)(?:[']s)? name is (\w+)",
        r'(?:baby|son|daughter|child) (?:named|called) (\w+)',
        r'(\w+) is (?:my|our) (?:baby|son|daughter|child)'
    ],
    "baby_gender": [
        r'(?:my|our) (son|daughter|boy|girl)',
        r'(he|she) is (\d+)',
        r'(male|female) baby'
    ],
    "budget": [
        r'[\$₪€£](\d+)',
        r'budget (?:of|is) [\$₪€£]?(\d+)',
        r'spend (?:up to|around) [\$₪€£]?(\d+)',
        r'(\d+) (?:dollars|shekels|euros|pounds)'
    ],
    "health_conditions": [
        r'(?:has|diagnosed with|suffers from) (allergy|allergies|eczema|reflux|colic|fever)',
        r'(?:has|diagnosed with|suffers from) ([a-zA-Z\s]+) allergy',
        r'allergic to ([a-zA-Z\s]+)',
        r'(fever|rash|cough|cold|flu|ear infection)',
        r'has a (?:slight|high|low)? (fever)',
        r'has (?:slight|high|low)? (fever)',
        r'(?:slight|high|low)? (fever)',
        r'(?:isn\'t|not) (?:eating|sleeping) (?:well|properly)',
        r'(sick|ill|unwell)',
        r'(temperature|thermometer) (?:shows|reads|is) (\d+(?:\.\d+)?)',
        r'baby (?:has|with|showing) (?:a )?(fever|rash|cough|cold|flu|ear infection|allergy|eczema|reflux|colic)'
    ],
    "safety_concerns": [
        r'worried about (safety|accidents|falls|choking|drowning)',
        r'concerned about (safety|accidents|falls|choking|drowning)',
        r'how to (baby-proof|childproof|babyproof)',
        r'(baby-proofing|childproofing|babyproofing) (?:the|our) (house|home|apartment|room)',
        r'(kitchen|bathroom|bedroom|living room|stairs) safety',
        r'safety (?:in|for) (?:the|our) (kitchen|bathroom|bedroom|living room|stairs)',
        r'help with (kitchen|bathroom|bedroom|living room|stairs) safety',
        r'need help with (baby-proofing|childproofing|babyproofing)',
        r'(electrical|outlet|cord|furniture|cabinet|drawer) safety',
        r'(pool|water|bath|tub) safety',
        r'(car seat|stroller|carrier) safety'
    ]
}

# Node functions
def extract_context(state: BabywiseState) -> BabywiseState:
    """Extract context from messages and update state"""
    messages = state["messages"]
    context = state.get("context", {})
    extracted_entities = state.get("extracted_entities", set())
    
    try:
        # Process messages to extract context
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content
                
                # Extract baby age if not already extracted
                if "baby_age" not in extracted_entities:
                    for pattern in CONTEXT_PATTERNS["baby_age"]:
                        age_match = re.search(pattern, content, re.IGNORECASE)
                        if age_match:
                            value = int(age_match.group(1))
                            if "week" in pattern:
                                unit = "weeks"
                            elif "day" in pattern:
                                unit = "days"
                            elif "year" in pattern:
                                unit = "years"
                            else:
                                unit = "months"
                            
                            context["baby_age"] = {
                                "value": value,
                                "unit": unit
                            }
                            extracted_entities.add("baby_age")
                            logger.info(f"Extracted baby age: {value} {unit}")
                            break
                
                # Extract baby name if not already extracted
                if "baby_name" not in extracted_entities:
                    for pattern in CONTEXT_PATTERNS["baby_name"]:
                        name_match = re.search(pattern, content, re.IGNORECASE)
                        if name_match:
                            name = name_match.group(1)
                            context["baby_name"] = name
                            extracted_entities.add("baby_name")
                            logger.info(f"Extracted baby name: {name}")
                            break
                
                # Extract baby gender if not already extracted
                if "baby_gender" not in extracted_entities:
                    for pattern in CONTEXT_PATTERNS["baby_gender"]:
                        gender_match = re.search(pattern, content, re.IGNORECASE)
                        if gender_match:
                            gender_term = gender_match.group(1).lower()
                            if gender_term in ["son", "boy", "he", "male"]:
                                gender = "male"
                            elif gender_term in ["daughter", "girl", "she", "female"]:
                                gender = "female"
                            else:
                                continue
                            
                            context["baby_gender"] = gender
                            extracted_entities.add("baby_gender")
                            logger.info(f"Extracted baby gender: {gender}")
                            break
                
                # Extract budget information if not already extracted or if mentioned again
                if "budget" not in extracted_entities or any(word in content.lower() for word in ['budget', 'cost', 'spend', '$', '₪', '€', '£']):
                    for pattern in CONTEXT_PATTERNS["budget"]:
                        budget_match = re.search(pattern, content, re.IGNORECASE)
                        if budget_match:
                            value = int(budget_match.group(1))
                            
                            # Determine currency
                            if '$' in content:
                                currency = 'USD'
                            elif '₪' in content:
                                currency = 'ILS'
                            elif '€' in content:
                                currency = 'EUR'
                            elif '£' in content:
                                currency = 'GBP'
                            elif 'dollar' in content.lower():
                                currency = 'USD'
                            elif 'shekel' in content.lower():
                                currency = 'ILS'
                            elif 'euro' in content.lower():
                                currency = 'EUR'
                            elif 'pound' in content.lower():
                                currency = 'GBP'
                            else:
                                currency = 'USD'  # Default
                            
                            context["budget"] = {
                                "value": value,
                                "currency": currency
                            }
                            extracted_entities.add("budget")
                            logger.info(f"Extracted budget: {currency} {value}")
                            break
                
                # Extract health conditions (always check for new conditions)
                if "health_conditions" not in context:
                    context["health_conditions"] = []
                
                # Check for specific health-related phrases in the content
                if "isn't eating" in content.lower() or "not eating" in content.lower():
                    if "eating problems" not in context["health_conditions"]:
                        context["health_conditions"].append("eating problems")
                        logger.info(f"Extracted health condition: eating problems")
                
                if "isn't sleeping" in content.lower() or "not sleeping" in content.lower():
                    if "sleeping problems" not in context["health_conditions"]:
                        context["health_conditions"].append("sleeping problems")
                        logger.info(f"Extracted health condition: sleeping problems")
                
                # Check for fever mentions specifically
                fever_patterns = [
                    r'(?:slight|high|low)? ?fever',
                    r'temperature',
                    r'running a fever',
                    r'has a fever'
                ]
                
                for pattern in fever_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        if "fever" not in context["health_conditions"]:
                            context["health_conditions"].append("fever")
                            logger.info(f"Extracted health condition: fever")
                            break
                
                # Check other health conditions using regex patterns
                for pattern in CONTEXT_PATTERNS["health_conditions"]:
                    health_match = re.search(pattern, content, re.IGNORECASE)
                    if health_match:
                        # Handle the case where there might be multiple capture groups
                        condition = health_match.group(1).lower() if health_match.lastindex and health_match.lastindex >= 1 else None
                        if condition and condition not in context["health_conditions"]:
                            context["health_conditions"].append(condition)
                            logger.info(f"Extracted health condition: {condition}")
                
                # Extract safety concerns (always check for new concerns)
                if "safety_concerns" not in context:
                    context["safety_concerns"] = []
                
                for pattern in CONTEXT_PATTERNS["safety_concerns"]:
                    safety_match = re.search(pattern, content, re.IGNORECASE)
                    if safety_match:
                        concern = safety_match.group(1).lower()
                        if concern not in context["safety_concerns"]:
                            context["safety_concerns"].append(concern)
                            logger.info(f"Extracted safety concern: {concern}")
        
        # Update state with new context and tracked entities
        state["context"] = context
        state["extracted_entities"] = extracted_entities
        logger.info(f"Updated context: {json.dumps(context, default=str)}")
        logger.info(f"Extracted entities: {extracted_entities}")
        return state
        
    except Exception as e:
        logger.error(f"Error extracting context: {str(e)}", exc_info=True)
        return state

def select_domain(state: BabywiseState) -> BabywiseState:
    """Select the appropriate domain based on the latest message"""
    try:
        messages = state["messages"]
        context = state.get("context", {})
        
        # If no messages, return general domain
        if not messages:
            state["domain"] = "general"
            return state
        
        # Get the latest message
        latest_msg = messages[-1].content.lower()
        
        # Define domain-specific keywords
        sleep_keywords = ["sleep", "nap", "bedtime", "night", "wake", "crib", "bassinet", 
                         "swaddle", "dream feed", "sleep training", "drowsy", "routine"]
        
        feeding_keywords = ["feed", "eat", "milk", "formula", "breast", "bottle", "nursing",
                           "solids", "puree", "spoon", "hunger", "appetite", "burp"]
        
        gear_keywords = ["stroller", "crib", "car seat", "carrier", "toy", "product", "gear",
                        "monitor", "diaper", "clothes", "swing", "bouncer", "playmat"]
        
        development_keywords = ["milestone", "develop", "growth", "skill", "learn", "crawl", 
                               "walk", "talk", "roll", "sit", "stand", "grasp", "smile", "laugh"]
        
        health_safety_keywords = ["safety", "health", "sick", "fever", "rash", "vaccine", "doctor", 
                                 "medicine", "emergency", "first aid", "baby-proof", "childproof", 
                                 "babyproof", "accident", "injury", "safe", "hazard", "protection", 
                                 "car seat", "bath", "hygiene", "temperature", "sunscreen", "cold", 
                                 "flu", "virus", "infection", "allergy", "choking"]
        
        # Give higher weight to critical health keywords
        critical_health_keywords = ["fever", "sick", "emergency", "injury", "medicine", "doctor", "rash", "infection"]
        
        # Check if there are health conditions in the context
        has_health_conditions = bool(context.get("health_conditions", []))
        
        # Count keyword matches for each domain
        sleep_count = sum(1 for word in sleep_keywords if word in latest_msg)
        feeding_count = sum(1 for word in feeding_keywords if word in latest_msg)
        gear_count = sum(1 for word in gear_keywords if word in latest_msg)
        development_count = sum(1 for word in development_keywords if word in latest_msg)
        
        # Health safety count with extra weight for critical terms
        health_safety_count = sum(1 for word in health_safety_keywords if word in latest_msg)
        health_safety_count += sum(2 for word in critical_health_keywords if word in latest_msg)
        
        # Add extra weight if there are health conditions in the context
        if has_health_conditions:
            health_safety_count += 3
            
        # Check for follow-up questions about previous health topics
        if "health_conditions" in context and context["health_conditions"]:
            for condition in context["health_conditions"]:
                if condition in latest_msg:
                    health_safety_count += 2
        
        # Select domain with most keyword matches
        domain_counts = {
            "sleep": sleep_count,
            "feeding": feeding_count,
            "baby_gear": gear_count,
            "development": development_count,
            "health_safety": health_safety_count
        }
        
        # If no keywords matched or tied, check previous domain for continuity
        max_count = max(domain_counts.values())
        if max_count == 0:
            # Check if asking about previous domain
            if "what about" in latest_msg or "how about" in latest_msg or "and also" in latest_msg:
                # Keep previous domain if it exists
                if "domain" in state and state["domain"] != "general":
                    domain = state["domain"]
                else:
                    domain = "general"
            else:
                domain = "general"
        else:
            # Get domain with highest count (if tied, prioritize in order: health_safety, sleep, feeding, development, gear)
            priority_order = ["health_safety", "sleep", "feeding", "development", "baby_gear"]
            max_domains = [d for d, count in domain_counts.items() if count == max_count]
            
            # Sort by priority
            for priority_domain in priority_order:
                if priority_domain in max_domains:
                    domain = priority_domain
                    break
            else:
                domain = "general"
        
        state["domain"] = domain
        logger.info(f"Selected domain: {domain}")
        return state
        
    except Exception as e:
        logger.error(f"Error selecting domain: {str(e)}", exc_info=True)
        state["domain"] = "general"
        return state

def generate_response(state: BabywiseState) -> BabywiseState:
    """Generate a response based on the current domain and context"""
    try:
        messages = state["messages"]
        context = state.get("context", {})
        domain = state.get("domain", "general")
        language = state.get("language", "en")
        
        # Format context string
        context_str = ""
        
        # Add baby age if available
        if "baby_age" in context:
            context_str += f"Baby age: {context['baby_age']['value']} {context['baby_age']['unit']}. "
        
        # Add baby name if available
        if "baby_name" in context:
            context_str += f"Baby name: {context['baby_name']}. "
        
        # Add baby gender if available
        if "baby_gender" in context:
            context_str += f"Baby gender: {context['baby_gender']}. "
        
        # Add budget if available
        if "budget" in context:
            context_str += f"Budget: {context['budget']['currency']} {context['budget']['value']}. "
        
        # Add health conditions if available
        if "health_conditions" in context and context["health_conditions"]:
            conditions = ", ".join(context["health_conditions"])
            context_str += f"Health conditions: {conditions}. "
        else:
            context_str += "No specific health conditions mentioned. "
        
        # Add safety concerns if available
        if "safety_concerns" in context and context["safety_concerns"]:
            concerns = ", ".join(context["safety_concerns"])
            context_str += f"Safety concerns: {concerns}. "
        
        # If no context provided, add a note
        if not context_str:
            context_str = "No specific context provided."
        
        # Get domain-specific prompt
        domain_prompt = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])
        
        # Add language instruction
        language_instruction = f"\nIMPORTANT: Respond in {language} language. The user is communicating in {language}."
        
        # Add additional instructions based on domain
        additional_instructions = ""
        
        if domain == "health_safety":
            # Check if critical information is missing for health-related queries
            missing_info = []
            
            # For health conditions, check if baby age is available (critical for health advice)
            if "health_conditions" in context and context["health_conditions"] and "baby_age" not in context:
                missing_info.append("baby's age")
            
            # For fever specifically, check if temperature details are available
            if "health_conditions" in context and "fever" in context["health_conditions"]:
                # Check if temperature was mentioned in any message
                temp_mentioned = False
                for msg in messages:
                    if isinstance(msg, HumanMessage) and re.search(r'(\d+(?:\.\d+)?)[°\s]?[CF]', msg.content):
                        temp_mentioned = True
                        break
                
                if not temp_mentioned:
                    missing_info.append("temperature reading")
            
            if missing_info:
                additional_instructions = f"\nIMPORTANT: The user has not provided the following critical information: {', '.join(missing_info)}. "
                additional_instructions += "Consider asking for this information if it's essential for providing accurate advice, but only if you don't have enough context to give a helpful general response."
        
        elif domain == "sleep":
            # Check if baby age is available (critical for sleep advice)
            if "baby_age" not in context:
                additional_instructions = "\nIMPORTANT: The user has not provided the baby's age, which is often critical for providing appropriate sleep advice. "
                additional_instructions += "Consider asking for this information if it's essential for your response, but only if you don't have enough context to give a helpful general response."
        
        elif domain == "feeding":
            # Check if baby age is available (critical for feeding advice)
            if "baby_age" not in context:
                additional_instructions = "\nIMPORTANT: The user has not provided the baby's age, which is essential for providing appropriate feeding advice. "
                additional_instructions += "Consider asking for this information if it's essential for your response, but only if you don't have enough context to give a helpful general response."
        
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
        
        elif domain == "development":
            # Check if baby age is available (critical for development advice)
            if "baby_age" not in context:
                additional_instructions = "\nIMPORTANT: The user has not provided the baby's age, which is essential for providing appropriate developmental guidance. "
                additional_instructions += "Consider asking for this information if it's essential for your response, but only if you don't have enough context to give a helpful general response."
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", domain_prompt + language_instruction + additional_instructions),
            MessagesPlaceholder(variable_name="messages"),
            ("system", f"Current context: {context_str}")
        ])
        
        # Generate response
        model = ChatOpenAI(temperature=0.7)
        chain = prompt | model
        response = chain.invoke({"messages": messages})
        
        # Add response to messages
        state["messages"].append(response)
        
        logger.info(f"Generated response for domain: {domain}")
        logger.info(f"State summary - Domain: {domain}, Messages: {len(state['messages'])}, Context: {json.dumps(context, default=str)}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
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
        
        state["messages"].append(AIMessage(content=error_message))
        return state

def post_process(state: BabywiseState) -> BabywiseState:
    """Perform any post-processing on the state"""
    # Add timestamp to metadata
    if "metadata" not in state:
        state["metadata"] = {}
    
    state["metadata"]["last_updated"] = datetime.utcnow().isoformat()
    
    # Log the current state summary
    try:
        context_summary = json.dumps(state.get("context", {}), default=str)
        domain = state.get("domain", "general")
        message_count = len(state.get("messages", []))
        
        logger.info(f"State summary - Domain: {domain}, Messages: {message_count}, Context: {context_summary}")
    except Exception as e:
        logger.error(f"Error logging state summary: {str(e)}")
    
    return state

# Create the workflow
def create_workflow():
    """Create the LangGraph workflow"""
    # Initialize the graph
    workflow = StateGraph(state_schema=BabywiseState)
    
    # Add nodes
    workflow.add_node("extract_context", extract_context)
    workflow.add_node("select_domain", select_domain)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("post_process", post_process)
    
    # Add edges
    workflow.add_edge("extract_context", "select_domain")
    workflow.add_edge("select_domain", "generate_response")
    workflow.add_edge("generate_response", "post_process")
    
    # Set entry point
    workflow.set_entry_point("extract_context")
    
    # Compile the workflow
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# Global memory store for all workflows
memory_saver = MemorySaver()
# Global workflow instance
_workflow = None

def get_workflow():
    """Get or create the workflow"""
    global _workflow
    if _workflow is None:
        # Initialize the graph
        workflow = StateGraph(state_schema=BabywiseState)
        
        # Add nodes
        workflow.add_node("extract_context", extract_context)
        workflow.add_node("select_domain", select_domain)
        workflow.add_node("generate_response", generate_response)
        workflow.add_node("post_process", post_process)
        
        # Add edges
        workflow.add_edge("extract_context", "select_domain")
        workflow.add_edge("select_domain", "generate_response")
        workflow.add_edge("generate_response", "post_process")
        
        # Set entry point
        workflow.set_entry_point("extract_context")
        
        # Compile the workflow with the global memory saver
        _workflow = workflow.compile(checkpointer=memory_saver)
    
    return _workflow

# Helper functions
def get_default_state() -> BabywiseState:
    """Get the default state"""
    return {
        "messages": [],
        "context": {},
        "domain": "general",
        "extracted_entities": set(),
        "language": "en",
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "language": "en"
        }
    }

def add_user_message(state: BabywiseState, message: str) -> BabywiseState:
    """Add a user message to the state"""
    state["messages"].append(HumanMessage(content=message))
    return state

# Thread state cache
thread_states = {}

# Main chat function
async def chat(message: str, thread_id: str, language: str = "en") -> Dict[str, Any]:
    """Process a chat message and return a response"""
    try:
        # Get the workflow
        workflow = get_workflow()
        
        # Configure the workflow with the thread ID
        config = {"configurable": {"thread_id": thread_id}}
        
        # Check if we have existing state for this thread
        if thread_id in thread_states:
            # Get existing state
            logger.info(f"Using existing state for thread {thread_id}")
            state = thread_states[thread_id]
            
            # Add the new user message
            state["messages"].append(HumanMessage(content=message))
            
            # Update language in state
            state["language"] = language
        else:
            # Try to retrieve state from memory
            try:
                logger.info(f"Attempting to retrieve state from memory for thread {thread_id}")
                state = memory_saver.get(thread_id)
                logger.info(f"Retrieved state from memory for thread {thread_id}")
                
                # Add the new user message
                state["messages"].append(HumanMessage(content=message))
                
                # Update language in state
                state["language"] = language
            except Exception as e:
                # Create new state if not found in memory
                logger.info(f"Creating new state for thread {thread_id}: {str(e)}")
                state = get_default_state()
                state["messages"].append(HumanMessage(content=message))
                state["language"] = language
        
        # Run the workflow
        logger.info(f"Running workflow for thread {thread_id}")
        result = workflow.invoke(state, config)
        
        # Store the updated state
        thread_states[thread_id] = result
        
        # Extract the assistant's response
        assistant_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        response_text = assistant_messages[-1].content if assistant_messages else "I'm sorry, I couldn't generate a response."
        
        # Log the context for debugging
        logger.info(f"Context for thread {thread_id}: {json.dumps(result.get('context', {}), default=str)}")
        
        # Convert set to list for JSON serialization
        context_copy = result.get("context", {}).copy()
        
        return {
            "text": response_text,
            "domain": result["domain"],
            "context": context_copy,
            "metadata": result["metadata"],
            "language": language
        }
        
    except Exception as e:
        logger.error(f"Error in chat function: {str(e)}", exc_info=True)
        return {
            "text": "I apologize, but I encountered an error. Please try again.",
            "error": str(e),
            "language": language
        }

# Get context for a thread
def get_context(thread_id: str) -> Dict[str, Any]:
    """Get the current context for a thread"""
    try:
        # Check if we have existing state for this thread
        if thread_id in thread_states:
            state = thread_states[thread_id]
            return {
                "context": state.get("context", {}),
                "domain": state.get("domain", "general")
            }
        
        # Try to retrieve state from memory
        try:
            state = memory_saver.get(thread_id)
            return {
                "context": state.get("context", {}),
                "domain": state.get("domain", "general")
            }
        except Exception:
            return {
                "context": {},
                "domain": "general"
            }
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}", exc_info=True)
        return {
            "context": {},
            "domain": "general",
            "error": str(e)
        }

# Reset a thread
def reset_thread(thread_id: str) -> Dict[str, Any]:
    """Reset a thread's state"""
    try:
        # Remove from thread states if exists
        if thread_id in thread_states:
            del thread_states[thread_id]
        
        # Try to remove from memory
        try:
            memory_saver.delete(thread_id)
        except Exception:
            pass
        
        return {
            "success": True,
            "message": f"Thread {thread_id} has been reset"
        }
    except Exception as e:
        logger.error(f"Error resetting thread: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        } 