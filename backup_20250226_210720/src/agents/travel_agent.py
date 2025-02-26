from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class TravelAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        # Call parent class initialization first
        super().__init__(agent_type, name, llm_service)
        
        # Then set agent-specific attributes
        self.agent_type = AgentTypes.TRAVEL
        self.name = "Travel & Adventure Guide"
        self.logger = logging.getLogger(__name__)
        
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a Travel & Adventure Guide specializing in helping families travel with babies and young children.

Key Areas of Expertise:

1. Travel Planning
   - Age-appropriate destinations
   - Travel timing and duration
   - Route optimization
   - Accommodation selection
   - Transportation options
   - Schedule flexibility
   - Local resources

2. Safety & Health
   - Travel safety guidelines
   - Health precautions
   - Emergency preparedness
   - Insurance considerations
   - Medical accessibility
   - Documentation requirements
   - Local healthcare options

3. Travel Gear & Supplies
   - Essential equipment
   - Packing strategies
   - Baby-specific needs
   - Climate considerations
   - Storage solutions
   - Travel-friendly products
   - Weight restrictions

4. Transportation
   - Flight regulations
   - Car safety requirements
   - Public transport tips
   - Stroller considerations
   - Baby carrier options
   - Security procedures
   - Comfort measures

5. Destination Management
   - Baby-friendly locations
   - Rest stop planning
   - Feeding arrangements
   - Sleep considerations
   - Activity scheduling
   - Environmental factors
   - Cultural considerations

Always Consider:
- Baby's age and development stage
- Travel distance and duration
- Mode of transportation
- Climate and weather
- Medical facilities access
- Cultural differences
- Family preferences

Provide:
- Detailed planning guidance
- Safety precautions
- Packing checklists
- Schedule recommendations
- Emergency procedures
- Local resources
- Backup plans"""),
            ("human", """Query: {query}
Baby's Age: {baby_age}
Travel Type: {travel_type}
Destination: {destination}
Duration: {duration}
Special Needs: {special_needs}
Travel Concerns: {concerns}

Please provide:
1. Pre-travel preparation
2. Transportation guidance
3. Accommodation recommendations
4. Essential packing list
5. Daily care strategies
6. Safety considerations
7. Emergency procedures""")
        ])

    def get_agent_expertise(self) -> List[str]:
        """Return the agent's areas of expertise."""
        return [
            # Travel Types
            'travel', 'trip', 'flight', 'drive', 'vacation',
            'journey', 'adventure', 'outing', 'visit',
            # Transportation
            'plane', 'car', 'train', 'bus', 'ship',
            'stroller', 'carrier', 'carseat',
            # Planning
            'schedule', 'itinerary', 'route', 'plan',
            'booking', 'reservation', 'accommodation',
            # Safety & Health
            'safety', 'health', 'emergency', 'medical',
            'insurance', 'documents', 'passport',
            # Gear & Supplies
            'packing', 'supplies', 'equipment', 'gear',
            'essentials', 'checklist', 'luggage',
            # Hebrew
            'נסיעה', 'טיול', 'טיסה', 'נהיגה', 'חופשה',
            'מסע', 'הרפתקה', 'ביקור', 'תכנון'
        ]

    def get_required_fields(self) -> List[str]:
        """Return the required fields for travel-related queries."""
        return [
            'baby_age',
            'travel_type',
            'destination',
            'duration',
            'travel_mode'
        ]

    def get_agent_prompt(self) -> str:
        """Return the agent's system prompt."""
        return """You are a Travel & Adventure Guide specializing in helping families travel with babies and young children.

Key Areas of Expertise:

1. Travel Planning
   - Age-appropriate destinations
   - Travel timing and duration
   - Route optimization
   - Accommodation selection
   - Transportation options
   - Schedule flexibility
   - Local resources

2. Safety & Health
   - Travel safety guidelines
   - Health precautions
   - Emergency preparedness
   - Insurance considerations
   - Medical accessibility
   - Documentation requirements
   - Local healthcare options

3. Travel Gear & Supplies
   - Essential equipment
   - Packing strategies
   - Baby-specific needs
   - Climate considerations
   - Storage solutions
   - Travel-friendly products
   - Weight restrictions

4. Transportation
   - Flight regulations
   - Car safety requirements
   - Public transport tips
   - Stroller considerations
   - Baby carrier options
   - Security procedures
   - Comfort measures

5. Destination Management
   - Baby-friendly locations
   - Rest stop planning
   - Feeding arrangements
   - Sleep considerations
   - Activity scheduling
   - Environmental factors
   - Cultural considerations

Always Consider:
- Baby's age and development stage
- Travel distance and duration
- Mode of transportation
- Climate and weather
- Medical facilities access
- Cultural differences
- Family preferences

Provide:
- Detailed planning guidance
- Safety precautions
- Packing checklists
- Schedule recommendations
- Emergency procedures
- Local resources
- Backup plans"""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        gathered_info = {}
        try:
            for message in self.shared_memory.chat_memory.messages:
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
                
                # Extract travel type
                travel_types = {
                    'flight': ['fly', 'flight', 'plane', 'airport', 'airline'],
                    'car': ['drive', 'car', 'road trip', 'driving', 'vehicle'],
                    'train': ['train', 'rail', 'railway', 'station'],
                    'cruise': ['cruise', 'ship', 'boat', 'sea'],
                    'bus': ['bus', 'coach', 'shuttle']
                }
                
                for type_name, keywords in travel_types.items():
                    if any(keyword in content for keyword in keywords):
                        gathered_info["travel_type"] = {
                            'type': type_name,
                            'description': content
                        }
                        break
                
                # Extract destination information
                destination_patterns = [
                    r'to\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)*)',
                    r'in\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)*)',
                    r'visiting\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)*)'
                ]
                
                for pattern in destination_patterns:
                    match = re.search(pattern, content)
                    if match:
                        gathered_info["destination_info"] = {
                            'location': match.group(1).strip(),
                            'description': content
                        }
                        break
                
                # Extract duration
                duration_patterns = {
                    'days': r'(\d+)\s*days?',
                    'weeks': r'(\d+)\s*weeks?',
                    'months': r'(\d+)\s*months?'
                }
                
                for unit, pattern in duration_patterns.items():
                    match = re.search(pattern, content)
                    if match:
                        value = int(match.group(1))
                        gathered_info["duration"] = {
                            'value': value,
                            'unit': unit,
                            'original': f"{value} {unit}"
                        }
                        break
                
                # Extract special needs
                special_needs_keywords = {
                    'medical': ['medication', 'medical', 'health', 'condition'],
                    'dietary': ['allergy', 'food', 'diet', 'feeding'],
                    'equipment': ['gear', 'equipment', 'device', 'machine'],
                    'accessibility': ['access', 'wheelchair', 'stroller', 'mobility']
                }
                
                for need_type, keywords in special_needs_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        if "special_needs" not in gathered_info:
                            gathered_info["special_needs"] = {}
                        gathered_info["special_needs"][need_type] = content
                
                # Extract travel concerns
                concern_keywords = {
                    'safety': ['safe', 'security', 'danger', 'risk'],
                    'health': ['sick', 'illness', 'hospital', 'doctor'],
                    'comfort': ['comfort', 'sleep', 'cry', 'upset'],
                    'logistics': ['schedule', 'timing', 'delay', 'connection']
                }
                
                for concern_type, keywords in concern_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        if "travel_concerns" not in gathered_info:
                            gathered_info["travel_concerns"] = {}
                        gathered_info["travel_concerns"][concern_type] = content
            
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting travel context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # First extract context from the current query
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for missing critical information
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "To provide appropriate travel guidance, I need to know your baby's age and travel type (flight, car, etc.). Could you share this information?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            result = await self.llm_service.generate_response(
                self.prompt_template.format(
                    query=query,
                    baby_age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                    travel_type=gathered_info.get("travel_type", {}).get("type", "Not specified"),
                    destination=gathered_info.get("destination_info", {}).get("location", "Not specified"),
                    duration=gathered_info.get("duration", {}).get("original", "Not specified"),
                    special_needs=gathered_info.get("special_needs", {}),
                    concerns=gathered_info.get("travel_concerns", {})
                )
            )
            
            # Add age-specific safety reminders
            baby_age = gathered_info.get("baby_age", {}).get("value", 0)
            travel_type = gathered_info.get("travel_type", {}).get("type", "")
            
            safety_tips = "\n\nIMPORTANT TRAVEL SAFETY REMINDERS:"
            
            # Universal safety tips
            safety_tips += "\n- Always have a basic first aid kit"
            safety_tips += "\n- Keep emergency contacts readily available"
            safety_tips += "\n- Maintain regular feeding and changing schedule"
            safety_tips += "\n- Pack extra supplies for delays"
            
            # Age-specific tips
            if baby_age < 3:
                safety_tips += "\n\nFor babies under 3 months:"
                safety_tips += "\n- Consult pediatrician before travel"
                safety_tips += "\n- Avoid crowded places when possible"
                safety_tips += "\n- Monitor feeding and diaper changes closely"
                safety_tips += "\n- Be extra vigilant about hand hygiene"
            
            # Travel type specific tips
            if travel_type == "flight":
                safety_tips += "\n\nFor air travel:"
                safety_tips += "\n- Feed during takeoff/landing for ear pressure"
                safety_tips += "\n- Use an approved car seat or restraint device"
                safety_tips += "\n- Keep essential supplies in carry-on"
                safety_tips += "\n- Check airline policies for baby equipment"
            elif travel_type == "car":
                safety_tips += "\n\nFor car travel:"
                safety_tips += "\n- Use properly installed car seat"
                safety_tips += "\n- Plan frequent breaks (every 2-3 hours)"
                safety_tips += "\n- Never leave baby alone in car"
                safety_tips += "\n- Keep emergency supplies accessible"
            
            result.content += safety_tips
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in travel agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your travel-related question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is travel-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = [
            'travel', 'trip', 'flight', 'drive', 'journey',
            'vacation', 'holiday', 'destination', 'visit',
            'נסיעה', 'טיול', 'טיסה', 'נסיעה', 'חופשה'
        ]
        
        if any(term in query_lower for term in primary_terms):
            return 1.0
            
        # Secondary domain terms
        secondary_terms = [
            'pack', 'luggage', 'hotel', 'car', 'plane',
            'אריזה', 'מזוודה', 'מלון', 'רכב', 'מטוס'
        ]
        
        if any(term in query_lower for term in secondary_terms):
            return 0.7
            
        return 0.0

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'travel_type' not in gathered_info:
            missing.append('travel_type')
            return missing  # Get travel type next
            
        if 'destination_info' not in gathered_info:
            missing.append('destination_info')
            
        if 'duration' not in gathered_info:
            missing.append('duration')
        
        return missing
