from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class HealthAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        super().__init__(agent_type, name, llm_service)
        
        self.agent_type = AgentTypes.HEALTH
        self.name = "Health & Wellness Specialist"
        self.logger = logging.getLogger(__name__)

    def get_agent_expertise(self) -> List[str]:
        """Return the agent's areas of expertise."""
        return [
            # Medical Health
            'health', 'medical', 'symptoms', 'illness', 'fever',
            'vaccination', 'medicine', 'doctor', 'pediatrician',
            'emergency', 'first aid', 'safety', 'infection',
            # Mental Health
            'mental health', 'emotional', 'stress', 'anxiety',
            'depression', 'overwhelm', 'support', 'cope', 'mood',
            'therapy', 'counseling', 'self-care', 'burnout',
            # Hebrew
            'בריאות', 'רפואה', 'תסמינים', 'מחלה', 'חום',
            'חיסון', 'תרופה', 'רופא', 'חירום', 'בריאות נפשית',
            'רגשי', 'לחץ', 'חרדה', 'דיכאון', 'תמיכה'
        ]

    def get_required_fields(self) -> List[str]:
        """Return the required fields for health-related queries."""
        return ['baby_age', 'symptoms', 'duration', 'severity']

    def get_agent_prompt(self) -> str:
        """Return the agent's system prompt."""
        return """You are a comprehensive Health & Wellness Specialist supporting both physical and mental health needs.

Key Areas of Focus:

1. Physical Health
   - Common childhood illnesses and symptoms
   - Preventive care and vaccinations
   - Growth and development monitoring
   - Nutrition and feeding concerns
   - Sleep-related health issues
   - Emergency situations recognition

2. Mental & Emotional Health
   - Parental mental wellness
   - Postpartum adjustment
   - Anxiety and stress management
   - Depression screening
   - Family dynamics
   - Support system building

3. Integrated Care Approach
   - Mind-body connection
   - Holistic wellness strategies
   - Family-centered care
   - Preventive mental health
   - Stress impact on physical health

Emergency Protocols:
- Immediate recognition of critical situations
- Clear emergency response guidance
- When to seek immediate medical care
- Mental health crisis intervention

Always:
- Prioritize safety and well-being
- Consider both physical and emotional aspects
- Provide evidence-based information
- Maintain professional boundaries
- Recommend professional help when needed
- Include both immediate and long-term strategies
- Consider cultural and family context

IMPORTANT: This is not a substitute for professional medical or mental health care.
Always refer to healthcare providers for diagnosis and treatment."""

    def _extract_context_from_history(self) -> Dict[str, Any]:
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
                
                # Extract symptoms
                symptom_keywords = {
                    'physical': ['fever', 'cough', 'rash', 'vomit', 'diarrhea', 'pain'],
                    'mental': ['stress', 'anxiety', 'overwhelm', 'sad', 'worried', 'tired']
                }
                
                for category, keywords in symptom_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        if "symptoms" not in gathered_info:
                            gathered_info["symptoms"] = {}
                        gathered_info["symptoms"][category] = content
                
                # Extract duration
                duration_patterns = [
                    r'(\d+)\s*(day|week|hour|month)s?',
                    r'since\s+(yesterday|morning|afternoon|evening)',
                    r'started\s+(today|yesterday|last\s+week)'
                ]
                
                for pattern in duration_patterns:
                    match = re.search(pattern, content)
                    if match:
                        gathered_info["duration"] = {
                            'description': match.group(0),
                            'original': content
                        }
                        break
                
                # Extract severity
                severity_keywords = {
                    'high': ['severe', 'extreme', 'very', 'lot', 'unbearable'],
                    'medium': ['moderate', 'somewhat', 'quite', 'rather'],
                    'low': ['mild', 'slight', 'little', 'minor']
                }
                
                for level, keywords in severity_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        gathered_info["severity"] = {
                            'level': level,
                            'description': content
                        }
                        break
            
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting health context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Check for emergency keywords first
            emergency_keywords = ['choking', 'breathing', 'unconscious', 'seizure', 'severe', 'suicide', 'harm']
            if any(keyword in query.lower() for keyword in emergency_keywords):
                return {
                    "type": ResponseTypes.EMERGENCY,
                    "text": """EMERGENCY SITUATION - SEEK IMMEDIATE HELP

IF LIFE-THREATENING:
1. Call emergency services (911) immediately
2. Stay with the person
3. Follow emergency dispatcher instructions

FOR MENTAL HEALTH CRISIS:
- National Crisis Hotline (24/7): 988
- Suicide Prevention Lifeline: 1-800-273-8255
- Crisis Text Line: Text HOME to 741741

Do not delay seeking emergency care."""
                }
            
            # Extract and update context
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for missing critical information
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "To provide appropriate health guidance, I need more information. Could you please tell me about the symptoms and how long they've been present?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            result = await self.llm_service.generate_response(
                self.prompt_template.format(
                    query=query,
                    age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                    symptoms=gathered_info.get("symptoms", {}),
                    duration=gathered_info.get("duration", {}).get("description", "Not specified"),
                    severity=gathered_info.get("severity", {}).get("level", "Not specified"),
                    medical_history=gathered_info.get("medical_history", "Not specified"),
                    support_system=gathered_info.get("support_system", "Not specified")
                )
            )
            
            # Add medical disclaimer
            disclaimer = "\n\nIMPORTANT MEDICAL DISCLAIMER: This information is for educational purposes only and not a substitute for professional medical or mental health care. Always consult qualified healthcare providers for medical advice, diagnosis, or treatment."
            
            result.content += disclaimer
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in health agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your health-related question. If this is an emergency, please seek immediate medical attention."
            }

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'symptoms' not in gathered_info:
            missing.append('symptoms')
            return missing  # Get symptoms next
            
        if 'duration' not in gathered_info:
            missing.append('duration')
            
        if 'severity' not in gathered_info:
            missing.append('severity')
        
        return missing 