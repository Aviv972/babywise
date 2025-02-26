from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class BabyGearAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        super().__init__(agent_type, name, llm_service)
        
        self.agent_type = AgentTypes.BABY_GEAR
        self.name = "Baby Gear & Equipment Specialist"
        self.required_context = ['baby_age', 'budget_range', 'priority_needs', 'usage_context']
        
        self.logger = logging.getLogger(__name__)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Baby Gear & Equipment Specialist helping parents make informed decisions about baby products.

Key Areas of Expertise:

1. Essential Equipment Categories
   - Transportation (Strollers, Car Seats, Carriers)
   - Sleep (Cribs, Bassinets, Monitors)
   - Feeding (Bottles, Sterilizers, High Chairs)
   - Safety (Baby Proofing, Gates, Monitors)
   - Play & Development (Playmats, Toys, Activity Centers)
   - Care & Hygiene (Changing Tables, Bath Items)

2. Product Selection Criteria
   - Safety Standards & Certifications
   - Age-Appropriate Features""")
        ])

    def get_agent_expertise(self) -> List[str]:
        """Get the agent's areas of expertise."""
        return [
            # Transportation
            'stroller', 'car seat', 'carrier', 'travel system',
            # Sleep
            'crib', 'bassinet', 'monitor', 'swaddle', 'sleep sack',
            # Feeding
            'bottle', 'sterilizer', 'pump', 'high chair', 'nursing pillow',
            # Safety
            'baby proofing', 'gate', 'monitor', 'lock', 'guard',
            # Play & Development
            'playmat', 'toys', 'bouncer', 'activity center', 'books',
            # Care & Hygiene
            'changing table', 'diaper bag', 'bath', 'grooming', 'humidifier',
            # Hebrew
            'עגלה', 'סלקל', 'מיטה', 'בקבוק', 'צעצועים', 'אמבטיה'
        ]

    def get_required_fields(self) -> List[str]:
        return self.required_context

    def get_agent_prompt(self) -> str:
        """Get the agent's system prompt."""
        return f"""You are {self.name}, a specialized expert in baby gear and equipment.
        
        Your expertise covers:
        1. Transportation (Strollers, Car Seats, Carriers)
        2. Sleep Equipment (Cribs, Bassinets, Monitors)
        3. Feeding Supplies (Bottles, Sterilizers, High Chairs)
        4. Safety Products (Baby Proofing, Gates, Monitors)
        5. Play & Development Items (Playmats, Toys, Activity Centers)
        6. Care & Hygiene Products (Changing Tables, Bath Items)
        
        Guidelines:
        1. Always prioritize safety in recommendations
        2. Consider the baby's age and developmental stage
        3. Account for budget constraints
        4. Explain the reasoning behind recommendations
        5. Suggest alternatives when appropriate
        6. Include maintenance and care instructions
        7. Mention relevant safety standards
        8. Consider the family's lifestyle and needs
        
        Required Information:
        - Baby's age
        - Budget range
        - Priority needs
        - Usage context (home/travel/etc.)
        
        Remember to:
        - Focus on essential features
        - Explain pros and cons
        - Consider long-term value
        - Include safety warnings
        - Suggest complementary items
        - Provide care instructions"""

    def extract_agent_specific_context(self, message: str, gathered_info: Dict[str, Any]) -> Dict[str, Any]:
        # Extract specific gear preferences or requirements
        preferences = {}
        
        # Look for specific features or requirements
        feature_patterns = {
            "compact": r"(?i)(compact|small|lightweight|portable)",
            "storage": r"(?i)(storage|space|compartment)",
            "terrain": r"(?i)(terrain|all-terrain|smooth|rough|urban|city|off-road)",
            "travel": r"(?i)(travel|airplane|car|public transport)",
            "weather": r"(?i)(weather|rain|sun|hot|cold|winter|summer)"
        }
        
        for feature, pattern in feature_patterns.items():
            if re.search(pattern, message):
                preferences[feature] = True
        
        # Extract brand preferences
        brand_pattern = r"(?i)(prefer|want|like|looking for)\s+([A-Za-z]+)\s+(brand|stroller|car seat|crib)"
        brand_match = re.search(brand_pattern, message)
        if brand_match:
            preferences["preferred_brand"] = brand_match.group(2)
        
        # Update gathered_info with preferences if any were found
        if preferences:
            gathered_info["preferences"] = preferences
            
        return gathered_info

    def _get_system_prompt(self) -> str:
        return """You are a baby gear specialist helping parents choose appropriate equipment and products.
                 
                 Key Responsibilities:
                 1. Recommend age-appropriate gear
                 2. Consider budget constraints
                 3. Evaluate safety features
                 4. Compare product options
                 
                 Always:
                 - Prioritize safety in recommendations
                 - Consider age-specific needs
                 - Stay within budget constraints
                 - Explain key features and benefits
                 - Include maintenance tips
                 - Format responses in clear sections
                 - Provide specific product examples
                 - Include price ranges for recommendations
                 - Add safety warnings when relevant
                 
                 Remember: Focus on essential features that provide value
                 and avoid unnecessary expensive additions unless specifically requested."""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract gear-relevant information from conversation history"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        try:
            for message in messages:
                content = message.content.lower()
                
                # Extract age information using regex patterns
                month_patterns = [
                    r'(\d+)[\s-]month[\s-]old',  # "6 month old" or "6-month-old"
                    r'(\d+)[\s-]months[\s-]old',  # "6 months old" or "6-months-old"
                    r'(\d+)[\s-]month',           # "6 month" or "6-month"
                    r'(\d+)[\s-]months'           # "6 months" or "6-months"
                ]
                
                for pattern in month_patterns:
                    match = re.search(pattern, content)
                    if match:
                        age_value = int(match.group(1))
                        gathered_info["baby_age"] = {
                            "value": age_value,
                            "unit": "months",
                            "original": f"{age_value} months"
                        }
                        break
                
                # Extract budget information with currency detection
                if any(word in content for word in ['budget', 'cost', 'price', 'spend', '$', '₪']):
                    # Look for currency amounts with symbols
                    currency_matches = re.findall(r'[\$₪](\d+)', content)
                    if currency_matches:
                        # Use the first currency amount found
                        gathered_info["budget"] = {
                            "value": int(currency_matches[0]),
                            "currency": 'USD' if '$' in content else 'ILS',
                            "original": content
                        }
                    else:
                        # Look for numbers after budget-related words
                        for word in ['budget', 'cost', 'price', 'spend']:
                            if word in content:
                                # Find position of the word and look for numbers after it
                                pos = content.find(word)
                                remaining_text = content[pos:]
                                numbers = re.findall(r'\d+', remaining_text)
                                if numbers:
                                    gathered_info["budget"] = {
                                        "value": int(numbers[0]),
                                        "currency": "USD",  # Default to USD
                                        "original": content
                                    }
                                    break
                
                # Extract specific needs with categorization
                needs_keywords = ['need', 'looking for', 'want', 'require']
                if any(keyword in content for keyword in needs_keywords):
                    gathered_info["specific_needs"] = {
                        'type': 'requirement',
                        'description': content
                    }
                
                # Extract usage context with structured data
                if any(word in content for word in ['use', 'situation', 'purpose', 'activity']):
                    gathered_info["usage_context"] = {
                        'type': 'usage',
                        'description': content
                    }
                
                # Extract preferences with priority levels
                if any(word in content for word in ['prefer', 'like', 'important', 'must have']):
                    priority = 'high' if 'must have' in content else 'medium'
                    gathered_info["preferences"] = {
                        'type': 'preference',
                        'description': content,
                        'priority': priority
                    }
            
            self.logger.info(f"Extracted context: {gathered_info}")
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process baby gear queries with appropriate recommendations"""
        try:
            # First extract context from the current query
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for missing fields
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "To provide accurate gear recommendations, I need to know your budget and specific needs. Could you please provide this information?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            
            # Format the prompt variables
            prompt_vars = {
                "query": query,
                "baby_age": gathered_info.get("baby_age", {}).get("original", "Not specified"),
                "budget": f"{gathered_info.get('budget', {}).get('currency', 'USD')} {gathered_info.get('budget', {}).get('value', 'Not specified')}",
                "specific_needs": gathered_info.get("specific_needs", {}).get("description", "Not specified"),
                "usage_context": gathered_info.get("usage_context", {}).get("description", "Not specified"),
                "preferences": gathered_info.get("preferences", {}).get("description", "Not specified")
            }
            
            # Generate response using the prompt template
            result = await self.llm_service.generate_response(
                self.prompt_template.format(**prompt_vars)
            )
            
            # Add safety reminders based on age
            baby_age = gathered_info.get("baby_age", {}).get("value", 0)
            if baby_age < 6:
                result.content += "\n\nSAFETY REMINDER: For babies under 6 months, ensure the stroller has full recline capability and adequate head/neck support."
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in baby gear agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your gear-related question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is baby gear-related"""
        query_lower = query.lower()
        
        try:
            # Primary domain terms with categories
            primary_terms = {
                'transport': ['stroller', 'car seat', 'carrier', 'עגלה', 'סלקל', 'מנשא'],
                'sleep': ['crib', 'bassinet', 'monitor', 'מיטה', 'מוניטור'],
                'play': ['toys', 'playmat', 'צעצועים'],
                'general': ['gear', 'equipment', 'product', 'ציוד', 'מוצר']
            }
            
            for category, terms in primary_terms.items():
                if any(term in query_lower for term in terms):
                    self.logger.info(f"Found baby gear-specific terms in category: {category}")
            return 1.0
            
            # Secondary domain terms with intent
            secondary_terms = {
                'purchase': ['buy', 'purchase', 'לקנות'],
                'recommendation': ['recommend', 'suggest', 'להמליץ'],
                'need': ['need', 'want', 'require', 'צריך', 'רוצה']
            }
            
            for intent, terms in secondary_terms.items():
                if any(term in query_lower for term in terms):
                    self.logger.info(f"Found baby gear-related terms with intent: {intent}")
            return 0.7
            
            return 0.0  # Not baby gear-related
            
        except Exception as e:
            self.logger.error(f"Error calculating domain relevance: {str(e)}")
            return 0.0

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for baby gear advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
        
        if 'budget' not in gathered_info:
            missing.append('budget')
            return missing  # Get budget next
            
        if 'specific_needs' not in gathered_info:
            missing.append('specific_needs')
        
        return missing
