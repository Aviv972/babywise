from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class EmergencyAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        # Call parent class initialization first
        super().__init__(agent_type, name, llm_service)
        
        # Then set agent-specific attributes
        self.agent_type = AgentTypes.EMERGENCY
        self.name = "Emergency Response Expert"
        self.expertise = [
            'emergency', 'first aid', 'urgent care', 'safety', 'injury',
            'accident', 'medical', 'choking', 'breathing', 'fall',
            'bleeding', 'burn', 'poison', 'seizure', 'fever',
            'חירום', 'עזרה ראשונה', 'פציעה', 'חנק', 'נפילה'
        ]
        self.required_context = ['emergency_type', 'baby_age', 'symptoms']
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an emergency response expert specializing in baby emergencies.
            CRITICAL PRIORITIES:
            1. Immediate life-threatening situations
            2. Urgent medical attention needs
            3. First aid guidance
            4. Prevention and safety
            
            Always:
            - Assess situation severity immediately
            - Prioritize emergency services when needed
            - Provide clear, step-by-step instructions
            - Include what NOT to do
            - Add follow-up care guidance
            - Format responses for quick reading"""),
            ("human", """Emergency Query: {query}
            Baby's Age: {baby_age}
            Emergency Type: {emergency_type}
            Symptoms: {symptoms}
            Additional Context: {context}
            
            Provide IMMEDIATE guidance:
            1. Immediate safety steps
            2. Emergency response actions
            3. When to call emergency services
            4. What NOT to do
            5. Follow-up care needed""")
        ])

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract emergency-relevant information from conversation history"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        try:
            for message in messages:
                content = message.content.lower()
                
                # Extract age information
                month_patterns = [
                    r'(\d+)[\s-]month[\s-]old',
                    r'(\d+)[\s-]months[\s-]old',
                    r'(\d+)[\s-]month',
                    r'(\d+)[\s-]months'
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
                
                # Extract emergency type
                emergency_types = {
                    'breathing': ['choking', 'breathing', 'gasping', 'blue', 'חנק', 'נשימה'],
                    'injury': ['fall', 'hit', 'cut', 'bleeding', 'נפילה', 'מכה', 'חתך', 'דימום'],
                    'illness': ['fever', 'seizure', 'unconscious', 'חום', 'פרכוס', 'הכרה'],
                    'burn': ['burn', 'hot', 'scald', 'כוויה', 'חם'],
                    'poison': ['swallow', 'poison', 'chemical', 'בליעה', 'רעל']
                }
                
                for e_type, keywords in emergency_types.items():
                    if any(keyword in content for keyword in keywords):
                        gathered_info["emergency_type"] = {
                            'type': e_type,
                            'description': content
                        }
                        break
                
                # Extract symptoms
                if any(word in content for word in ['symptom', 'sign', 'showing', 'תסמין', 'סימן']):
                    gathered_info["symptoms"] = {
                        'description': content,
                        'timestamp': message.additional_kwargs.get('timestamp', '')
                    }
                
                # Extract severity indicators
                severity_keywords = ['severe', 'serious', 'worse', 'חמור', 'רציני', 'מחמיר']
                if any(keyword in content for keyword in severity_keywords):
                    gathered_info["severity"] = {
                        'level': 'high',
                        'description': content
                    }
            
            self.logger.info(f"Extracted emergency context: {gathered_info}")
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting emergency context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process emergency-related queries with immediate response"""
        try:
            # First extract context from the current query
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for immediate life-threatening emergencies
            critical_keywords = ['not breathing', 'choking', 'unconscious', 'seizure', 'severe bleeding']
            if any(keyword in query.lower() for keyword in critical_keywords):
                return {
                    "type": ResponseTypes.EMERGENCY,
                    "text": """CALL EMERGENCY SERVICES (911) IMMEDIATELY!

CRITICAL EMERGENCY RESPONSE:
1. Call 911 right now
2. Stay with the baby
3. Follow dispatcher instructions
4. Send someone to meet emergency services
5. Gather medical information if possible

DO NOT:
- Delay calling emergency services
- Leave the baby alone
- Give food or drink
- Move the baby if neck/spine injury suspected

Have ready for paramedics:
- Baby's age and weight
- Medical history
- What happened
- When it started
- Any medications"""
                }
            
            # Check for missing critical information
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "For proper emergency guidance, I need to know the type of emergency and your baby's age. Please provide this information immediately.",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            prompt = self.prompt_template.format(
                query=query,
                baby_age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                emergency_type=gathered_info.get("emergency_type", {}).get("description", "Not specified"),
                symptoms=gathered_info.get("symptoms", {}).get("description", "Not specified"),
                context=str(gathered_info)
            )
            
            result = await self.llm_service.generate_response(prompt)
            
            # Add emergency disclaimer
            disclaimer = "\n\nIMPORTANT: This is general guidance only. If you believe this is a medical emergency, do not wait - call emergency services (911) immediately. When in doubt, always seek professional medical care."
            
            result.content += disclaimer
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in emergency agent processing: {str(e)}")
            return {
                "type": ResponseTypes.EMERGENCY,
                "text": "If you believe this is an emergency, call emergency services (911) immediately."
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is emergency-related"""
        query_lower = query.lower()
        
        # Primary domain terms (immediate emergency)
        primary_terms = [
            'emergency', 'urgent', '911', 'help', 'choking', 'breathing',
            'unconscious', 'seizure', 'bleeding',
            'חירום', 'דחוף', 'עזרה', 'חנק', 'נשימה', 'דימום'
        ]
        
        if any(term in query_lower for term in primary_terms):
            self.logger.info("Found emergency-specific terms")
            return 1.0
            
        # Secondary domain terms
        secondary_terms = [
            'hurt', 'injury', 'accident', 'fall', 'burn', 'fever',
            'פציעה', 'תאונה', 'נפילה', 'כוויה', 'חום'
        ]
        
        if any(term in query_lower for term in secondary_terms):
            self.logger.info("Found emergency-related terms")
            return 0.7
            
        return 0.0  # Not emergency-related

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for emergency advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'emergency_type' not in gathered_info:
            missing.append('emergency_type')
            return missing  # Get emergency type first
            
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age next
            
        if 'symptoms' not in gathered_info:
            missing.append('symptoms')
        
        return missing 