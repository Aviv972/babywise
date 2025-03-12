"""
Babywise Chatbot - Context Extraction

This module implements the context extraction workflow node for the Babywise Chatbot.
It extracts relevant information from the conversation history, such as the baby's age,
name, gender, and other contextual details.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from backend.models.message_types import HumanMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
       r'(\d+)[\s-]year[s]?',
       # Additional patterns for conversational English
       r'my (?:son|daughter|baby) is (\d+) month[s]? old',
       r'my (?:son|daughter|baby) is (\d+) week[s]? old',
       r'my (?:son|daughter|baby) is (\d+) day[s]? old',
       r'my (?:son|daughter|baby) is (\d+) year[s]? old',
       r'my (?:son|daughter|baby) is (\d+) month[s]?',
       r'my (?:son|daughter|baby) is (\d+) week[s]?',
       r'my (?:son|daughter|baby) is (\d+) day[s]?',
       r'my (?:son|daughter|baby) is (\d+) year[s]?',
       # Handle textual numbers in English
       r'my (?:son|daughter|baby) is (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) month[s]? old',
       r'my (?:son|daughter|baby) is (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) week[s]? old',
       r'my (?:son|daughter|baby) is (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) month[s]?',
       r'my (?:son|daughter|baby) is (one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) week[s]?'
   ],
   # Hebrew patterns for age extraction
   "baby_age_hebrew": [
       r'בת (\d+) חודשים',      # girl X months old
       r'בת (\d+) שבועות',      # girl X weeks old
       r'בת (\d+) ימים',        # girl X days old
       r'בת (\d+) שנים',        # girl X years old
       r'בן (\d+) חודשים',      # boy X months old  
       r'בן (\d+) שבועות',      # boy X weeks old
       r'בן (\d+) ימים',        # boy X days old
       r'בן (\d+) שנים',        # boy X years old
       r'בת חודשיים',           # girl 2 months old (special case)
       r'בן חודשיים',           # boy 2 months old (special case)
       r'בת שבועיים',           # girl 2 weeks old (special case)
       r'בן שבועיים',           # boy 2 weeks old (special case)
       r'גיל (\d+) חודשים',     # age X months
       r'גיל (\d+) שבועות',     # age X weeks
       r'גיל (\d+) ימים',       # age X days
       r'גיל (\d+) שנים'        # age X years
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

async def extract_context(state: Dict[str, Any]) -> Dict[str, Any]:
   """Extract context from the conversation history"""
   try:
       logger.info("Starting extract_context function")
       messages = state["messages"]
       logger.info(f"Messages count: {len(messages)}")
       
       # Ensure context exists and is initialized as a dictionary
       if "context" not in state:
           state["context"] = {}
       context = state["context"]
       logger.info(f"Initial context: {context}")
       
       # Check if extracted_entities is a set, if not, convert it to a set
       if "extracted_entities" not in state:
           state["extracted_entities"] = set()
       elif not isinstance(state["extracted_entities"], set):
           # If it's a list or other iterable, convert to set
           try:
               state["extracted_entities"] = set(state["extracted_entities"])
           except:
               # If conversion fails, create a new set
               state["extracted_entities"] = set()
       
       # Define text number to numeric mapping for English
       text_to_number = {
           "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
           "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
           "eleven": 11, "twelve": 12
       }
       
       extracted_entities = state["extracted_entities"]
       logger.info(f"Initial extracted_entities: {extracted_entities}")
      
       # If no messages, return unchanged state
       if not messages:
           logger.info("No messages found, returning unchanged state")
           return state
      
       # Get the latest message
       latest_msg = messages[-1]
       logger.info(f"Latest message type: {latest_msg.type}")
       if latest_msg.type != "human":
           logger.info("Latest message is not from human, returning unchanged state")
           return state
       
       # Save context related to the conversation
       if "baby_age_mentioned" in extracted_entities and "baby_age" in context:
           # Store age mentioned in a separate variable to make it more accessible
           state["user_context"]["baby_age"] = context["baby_age"]["value"]
           state["user_context"]["baby_age_unit"] = context["baby_age"]["unit"]
           logger.info(f"Stored baby age in user_context: {state['user_context']['baby_age']} {state['user_context']['baby_age_unit']}")
       
       # Continue with the rest of the function
       content = latest_msg.content.lower()
       logger.info(f"Processing message content: {content[:50]}...")
      
       # Detect language
       language = "en"  # Default to English
       logger.info(f"Default language set to: {language}")
      
       # Check for Hebrew characters
       if re.search(r'[\u0590-\u05FF]', content):
           language = "he"
           logger.info("Detected Hebrew language")
           
           # Check for Hebrew breastfeeding/maternal terms
           hebrew_breastfeeding_terms = ["הנקה", "להניק", "מניקה", "חלב אם", "שאיבה", "שד", "פטמה"]
           hebrew_maternal_terms = ["לידה", "הריון", "קיסרי", "אמא", "אימא", "אחרי לידה"]
           
           # Set female context if breastfeeding or maternal terms are found
           if any(term in content for term in hebrew_breastfeeding_terms + hebrew_maternal_terms):
               logger.info("Detected Hebrew female context terms")
               if "user_context" not in state or state["user_context"] is None:
                   state["user_context"] = {}
               state["user_context"]["is_female_context"] = True
               logger.info("Set is_female_context to True")
               
               if any(term in content for term in hebrew_breastfeeding_terms):
                   state["user_context"]["is_breastfeeding_context"] = True
                   logger.info("Set is_breastfeeding_context to True")
                   
               if any(term in content for term in hebrew_maternal_terms):
                   state["user_context"]["is_maternal_context"] = True
                   logger.info("Set is_maternal_context to True")
      
       # Check for Arabic characters
       elif re.search(r'[\u0600-\u06FF]', content):
           language = "ar"
           logger.info("Detected Arabic language")
      
       # Update language in state
       state["language"] = language
       logger.info(f"Updated state language to: {language}")
      
       # Process messages to extract context
       for msg in messages:
           if msg.type == "human":
               content = msg.content
               
               # Special case handling for Hebrew "חודשיים" (two months)
               if language == "he" and "baby_age" not in extracted_entities:
                   if "בת חודשיים" in content:
                       context["baby_age"] = {
                           "value": 2,
                           "unit": "months",
                           "confidence": 0.9
                       }
                       extracted_entities.add("baby_age")
                       logger.info(f"Extracted baby age from Hebrew special case: 2 months")
                       
                   elif "בן חודשיים" in content:
                       context["baby_age"] = {
                           "value": 2,
                           "unit": "months",
                           "confidence": 0.9
                       }
                       extracted_entities.add("baby_age")
                       logger.info(f"Extracted baby age from Hebrew special case: 2 months")
               
               # Extract baby age if not already extracted - handle Hebrew first if detected
               if "baby_age" not in extracted_entities and language == "he":
                   for pattern in CONTEXT_PATTERNS["baby_age_hebrew"]:
                       age_match = re.search(pattern, content)
                       if age_match:
                           # Check if this is a special case (חודשיים/שבועיים)
                           if "חודשיים" in pattern or "שבועיים" in pattern:
                               value = 2  # These Hebrew words mean "two months"/"two weeks"
                           else:
                               # Regular number extraction
                               try:
                                   value = int(age_match.group(1))
                               except (IndexError, ValueError):
                                   value = None
                                   
                           if value is not None:
                               if "חודשים" in pattern or "חודשיים" in pattern:
                                   unit = "months"
                               elif "שבועות" in pattern or "שבועיים" in pattern:
                                   unit = "weeks"
                               elif "ימים" in pattern:
                                   unit = "days"
                               elif "שנים" in pattern:
                                   unit = "years"
                               else:
                                   unit = "months"  # Default
                              
                               context["baby_age"] = {
                                   "value": value,
                                   "unit": unit,
                                   "confidence": 0.9
                               }
                               extracted_entities.add("baby_age")
                               logger.info(f"Extracted baby age from Hebrew: {value} {unit}")
                               break
              
               # Extract baby age if not already extracted (English patterns)
               if "baby_age" not in extracted_entities:
                   for pattern in CONTEXT_PATTERNS["baby_age"]:
                       age_match = re.search(pattern, content, re.IGNORECASE)
                       if age_match:
                           # Check if it's a textual number
                           age_text = age_match.group(1).lower() 
                           if age_text in text_to_number:
                               value = text_to_number[age_text]
                           else:
                               try:
                                   value = int(age_text)
                               except ValueError:
                                   # If we can't convert to int, skip this match
                                   continue
                               
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
                               "unit": unit,
                               "confidence": 0.9  # Higher confidence for direct statements
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
                           context["baby_name"] = {
                               "value": name,
                               "confidence": 0.8
                           }
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
                          
                           context["baby_gender"] = {
                               "value": gender,
                               "confidence": 0.8
                           }
                           extracted_entities.add("baby_gender")
                           logger.info(f"Extracted baby gender: {gender}")
                           break
                           
               # For Hebrew, also extract gender from the text patterns
               if "baby_gender" not in extracted_entities and language == "he":
                   if "בת " in content:
                       gender = "female"
                       context["baby_gender"] = {
                           "value": gender,
                           "confidence": 0.8
                       }
                       extracted_entities.add("baby_gender")
                       logger.info(f"Extracted baby gender from Hebrew pattern: {gender}")
                   elif "בן " in content:
                       gender = "male"
                       context["baby_gender"] = {
                           "value": gender,
                           "confidence": 0.8
                       }
                       extracted_entities.add("baby_gender")
                       logger.info(f"Extracted baby gender from Hebrew pattern: {gender}")
              
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
                               "value": {
                                   "value": value,
                                   "currency": currency
                               },
                               "confidence": 0.8
                           }
                           extracted_entities.add("budget")
                           logger.info(f"Extracted budget: {currency} {value}")
                           break
              
               # Extract health conditions (always check for new conditions)
               health_conditions = []
               if "health_conditions" in context and "value" in context["health_conditions"]:
                   health_conditions = context["health_conditions"]["value"]
              
               # Check for specific health-related phrases in the content
               if "isn't eating" in content.lower() or "not eating" in content.lower():
                   if "eating problems" not in health_conditions:
                       health_conditions.append("eating problems")
                       logger.info(f"Extracted health condition: eating problems")
              
               if "isn't sleeping" in content.lower() or "not sleeping" in content.lower():
                   if "sleeping problems" not in health_conditions:
                       health_conditions.append("sleeping problems")
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
                       if "fever" not in health_conditions:
                           health_conditions.append("fever")
                           logger.info(f"Extracted health condition: fever")
                           break
              
               # Check other health conditions using regex patterns
               for pattern in CONTEXT_PATTERNS["health_conditions"]:
                   health_match = re.search(pattern, content, re.IGNORECASE)
                   if health_match:
                       # Handle the case where there might be multiple capture groups
                       condition = health_match.group(1).lower() if health_match.lastindex and health_match.lastindex >= 1 else None
                       if condition and condition not in health_conditions:
                           health_conditions.append(condition)
                           logger.info(f"Extracted health condition: {condition}")
              
               # Update health conditions in context
               if health_conditions:
                   context["health_conditions"] = {
                       "value": health_conditions,
                       "confidence": 0.8
                   }
                   extracted_entities.add("health_conditions")
              
               # Extract safety concerns (always check for new concerns)
               safety_concerns = []
               if "safety_concerns" in context and "value" in context["safety_concerns"]:
                   safety_concerns = context["safety_concerns"]["value"]
              
               for pattern in CONTEXT_PATTERNS["safety_concerns"]:
                   safety_match = re.search(pattern, content, re.IGNORECASE)
                   if safety_match:
                       concern = safety_match.group(1).lower()
                       if concern not in safety_concerns:
                           safety_concerns.append(concern)
                           logger.info(f"Extracted safety concern: {concern}")
              
               # Update safety concerns in context
               if safety_concerns:
                   context["safety_concerns"] = {
                       "value": safety_concerns,
                       "confidence": 0.8
                   }
                   extracted_entities.add("safety_concerns")
      
       logger.info(f"Updated context: {json.dumps(context, default=str)}")
       logger.info(f"Extracted entities: {extracted_entities}")
       logger.info("Completed extract_context function")
       return state
   except Exception as e:
       logger.error(f"Error in extract_context: {str(e)}", exc_info=True)
       # Return the original state in case of error
       return state 