from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class FeedingAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        super().__init__(agent_type, name, llm_service)
        
        self.agent_type = AgentTypes.FEEDING
        self.name = "Feeding & Nutrition Specialist"
        self.required_context = ['baby_age', 'feeding_type', 'current_schedule', 'concerns']
        
        self.logger = logging.getLogger(__name__)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Feeding & Nutrition Specialist helping parents with all aspects of infant feeding.

Key Areas of Expertise:

1. Breastfeeding Support
   - Latch techniques
   - Milk supply management
   - Pumping and storage
   - Common challenges
   - Maternal nutrition
   - Weaning strategies

2. Bottle Feeding Guidance
   - Formula selection
   - Safe preparation
   - Sterilization methods
   - Feeding positions
   - Amount guidelines
   - Transition strategies

3. Solid Food Introduction
   - Readiness signs
   - First foods
   - Texture progression
   - Baby-led weaning
   - Food safety
   - Allergy awareness

4. Nutrition Planning
   - Age-appropriate needs
   - Balanced nutrition
   - Meal scheduling
   - Portion guidance
   - Supplement needs
   - Special diets

5. Common Challenges
   - Reflux management
   - Colic strategies
   - Food sensitivities
   - Feeding difficulties
   - Growth concerns
   - Behavioral issues

Always Consider:
- Age-specific requirements
- Individual development
- Medical conditions
- Cultural preferences
- Family dynamics
- Environmental factors
- Safety guidelines

Provide:
- Evidence-based recommendations
- Clear instructions
- Safety precautions
- Troubleshooting tips
- Progress indicators
- Warning signs
- Professional referral guidance"""),
            ("human", """Query: {query}
Baby's Age: {baby_age}
Feeding Type: {feeding_type}
Current Schedule: {current_schedule}
Specific Concerns: {concerns}
Medical History: {medical_history}
Recent Changes: {recent_changes}

Please provide:
1. Age-appropriate recommendations
2. Safety guidelines
3. Practical implementation steps
4. Common challenges and solutions
5. Progress monitoring tips
6. Warning signs to watch
7. When to seek professional help""")
        ])

    def get_agent_expertise(self) -> List[str]:
        """Get the agent's areas of expertise."""
        return [
            # Breastfeeding
            'breastfeeding', 'nursing', 'lactation', 'milk supply',
            'pumping', 'latching', 'breast milk storage',
            # Bottle Feeding
            'formula', 'bottle', 'sterilization', 'preparation',
            # Solid Foods
            'solids', 'weaning', 'purees', 'finger foods',
            'baby led weaning', 'food introduction',
            # Nutrition
            'nutrition', 'diet', 'allergies', 'supplements',
            'meal planning', 'portions', 'feeding schedule',
            # Common Concerns
            'reflux', 'colic', 'gas', 'spitting up',
            'weight gain', 'feeding difficulties',
            # Hebrew
            'הנקה', 'תמ״ל', 'מזון', 'תזונה', 'אלרגיות',
            'ארוחות', 'בקבוק', 'מוצקים'
        ]

    def get_required_fields(self) -> List[str]:
        return self.required_context

    def get_agent_prompt(self) -> str:
        return """You are a Feeding Specialist helping parents with all aspects of baby feeding.

Your expertise includes:
1. Breastfeeding support and guidance
2. Bottle feeding best practices
3. Formula selection and preparation
4. Introduction to solid foods
5. Age-appropriate feeding schedules
6. Common feeding challenges
7. Nutrition guidelines

When responding:
1. Consider the baby's age and developmental stage
2. Provide evidence-based recommendations
3. Address safety concerns
4. Include practical tips and techniques
5. Suggest feeding schedules and routines
6. Mention common challenges and solutions
7. Emphasize responsive feeding practices

If you don't have enough information about the baby's age, current feeding method, or schedule, ask for clarification."""

    def extract_agent_specific_context(self, message: str, gathered_info: Dict[str, Any]) -> Dict[str, Any]:
        # Extract feeding type and preferences
        feeding_patterns = {
            "breastfeeding": r"(?i)(breast|nursing|breastfeed|milk supply|latch)",
            "bottle_feeding": r"(?i)(bottle|formula|pump|expressed milk)",
            "solids": r"(?i)(solid|food|puree|baby led|weaning)"
        }
        
        context = {}
        
        # Identify feeding type
        for feed_type, pattern in feeding_patterns.items():
            if re.search(pattern, message):
                context["feeding_type"] = feed_type
                break
        
        # Extract schedule information
        schedule_pattern = r"(?i)(\d+)\s*(time|hour|hr|times|feeds|feedings)"
        schedule_match = re.search(schedule_pattern, message)
        if schedule_match:
            context["schedule"] = {
                "frequency": int(schedule_match.group(1)),
                "unit": schedule_match.group(2),
                "original": schedule_match.group(0)
            }
        
        # Extract specific challenges
        challenges = []
        challenge_keywords = [
            "refusing", "spitting", "vomiting", "choking",
            "gagging", "fussy", "crying", "not eating"
        ]
        
        for keyword in challenge_keywords:
            if keyword in message.lower():
                challenges.append(keyword)
        
        if challenges:
            context["feeding_challenges"] = challenges
            
        # Update gathered_info with any found context
        if context:
            gathered_info.update(context)
            
        return gathered_info

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract feeding-relevant information from conversation history"""
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
                
                # Extract feeding type with more comprehensive matching
                feeding_types = {
                    'breastfeeding': ['breast', 'nursing', 'breastfeed'],
                    'formula': ['formula', 'bottle', 'תמ״ל'],
                    'solids': ['solid', 'food', 'puree', 'מזון'],
                    'mixed': ['mixed', 'combination', 'both']
                }
                
                for feeding_type, keywords in feeding_types.items():
                    if any(keyword in content for keyword in keywords):
                        gathered_info["feeding_type"] = feeding_type
                        break
                
                # Extract schedule information
                if any(word in content for word in ['every', 'hours', 'schedule', 'routine', 'times']):
                    gathered_info["current_schedule"] = {
                        'type': 'feeding',
                        'description': content
                    }
                
                # Extract feeding concerns
                if any(word in content for word in ['concern', 'worry', 'issue', 'problem']):
                    gathered_info["feeding_concerns"] = {
                        'type': 'concern',
                        'description': content
                    }
            
            self.logger.info(f"Extracted context: {gathered_info}")
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process feeding-related queries with age-appropriate recommendations"""
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
                    "text": "To provide accurate feeding advice, I need to know your baby's current feeding schedule. Could you tell me more about that?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            prompt = self.prompt_template.format(
                query=query,
                baby_age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                feeding_type=gathered_info.get("feeding_type", "Not specified"),
                current_schedule=gathered_info.get("current_schedule", {}).get("description", "Not specified"),
                context=str(gathered_info)
            )
            
            result = await self.llm_service.generate_response(prompt)
            
            # Add safety reminder for young babies
            baby_age = gathered_info.get("baby_age", {}).get("value", 0)
            if baby_age < 4:
                result.content += "\n\nIMPORTANT SAFETY NOTE: For babies under 4 months, breast milk or formula should be the only source of nutrition. Always consult your pediatrician before introducing any new foods or changing feeding patterns."
            elif baby_age < 6:
                result.content += "\n\nIMPORTANT SAFETY NOTE: Between 4-6 months, discuss with your pediatrician when to start introducing solid foods. Continue breast milk or formula as the primary source of nutrition."
            
            # Log successful response
            self.logger.info("Successfully generated feeding advice")
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in feeding agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your feeding-related question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is feeding-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = ['feed', 'breast', 'bottle', 'formula', 'solid', 'האכלה', 'הנקה', 'בקבוק', 'תמ״ל', 'מזון']
        
        if any(term in query_lower for term in primary_terms):
            print("Found feeding-specific terms")
            return 1.0
            
        # Secondary domain terms
        secondary_terms = ['milk', 'hunger', 'schedule', 'wean', 'nutrition', 'חלב', 'רעב', 'גמילה', 'תזונה']
        
        if any(term in query_lower for term in secondary_terms):
            print("Found feeding-related terms")
            return 0.7
            
        return 0.0  # Not feeding-related

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for feeding advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'feeding_type' not in gathered_info:
            missing.append('feeding_type')
            return missing  # Get feeding type next
            
        if 'current_schedule' not in gathered_info:
            missing.append('current_schedule')
        
        return missing
