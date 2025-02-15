from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class EmergencyAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Emergency Response Expert",
            expertise=[
                # English keywords
                "emergency", "urgent", "accident", "choking", "breathing",
                "injury", "fall", "burn", "bleeding", "unconscious",
                "poison", "seizure", "ambulance", "first aid", "911",
                # Hebrew keywords
                "חירום", "דחוף", "תאונה", "חנק", "נשימה",
                "פציעה", "נפילה", "כוויה", "דימום", "הכרה",
                "הרעלה", "פרכוס", "אמבולנס", "עזרה ראשונה", "מדא"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "current_status",
            "incident_time",
            "symptoms",
            "prior_conditions"
        ]
        
        # Emergency type specific questions
        self.context_questions_map = {
            "choking": [
                "consciousness_state",
                "breathing_status",
                "object_involved",
                "time_elapsed",
                "current_color"
            ],
            "fall": [
                "height_of_fall",
                "landing_surface",
                "impact_location",
                "movement_status",
                "visible_injuries"
            ],
            "burn": [
                "burn_source",
                "affected_area",
                "burn_appearance",
                "pain_level",
                "first_aid_applied"
            ],
            "fever": [
                "temperature",
                "duration",
                "other_symptoms",
                "medication_given",
                "fluid_intake"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As an emergency response expert, provide immediate guidance about: {query}

              EMERGENCY FRAMEWORK:
              1. Immediate Action Steps
                 - Call emergency services
                 - Safety measures
                 - First response steps
                 - What NOT to do
              
              2. Assessment Protocol
                 - Vital signs check
                 - Consciousness level
                 - Breathing status
                 - Injury evaluation
              
              3. First Aid Guidance
                 - Step-by-step instructions
                 - Required supplies
                 - Positioning
                 - Monitoring points
              
              4. While Waiting for Help
                 - Ongoing monitoring
                 - Comfort measures
                 - Documentation needs
                 - Preparation for EMS
              
              CRITICAL NOTICE:
              - Call emergency services immediately for serious situations
              - This is guidance only while waiting for professional help
              - Follow emergency dispatcher instructions
              - Document incident time and details
              
              Respond in the same language as the question.""" 

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Emergency confidence for '{query}': {confidence}")
        return confidence > 0.2 

    def _identify_emergency_type(self, query: str) -> Optional[str]:
        emergency_keywords = {
            "choking": ["choke", "stuck", "airway", "חנק", "נתקע", "נשימה"],
            "fall": ["fall", "dropped", "hit head", "נפילה", "נפל", "מכה בראש"],
            "burn": ["burn", "hot", "scald", "כוויה", "חם", "נכווה"],
            "fever": ["fever", "temperature", "hot", "חום", "חם", "טמפרטורה"]
        }
        
        query_lower = query.lower()
        for etype, keywords in emergency_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return etype
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "emergency preparedness info",
                "first aid basics",
                "safety planning",
                "emergency contact guidance",
                "prevention tips",
                "when to seek help"
            ],
            "cannot_do": [
                "emergency medical advice",
                "crisis intervention",
                "medical diagnosis",
                "treatment instructions",
                "medication guidance",
                "triage decisions"
            ],
            "refer_to": {
                "medical_emergency": "call emergency services immediately (911/112/101)",
                "poisoning": "poison control center",
                "severe_injury": "emergency room/ambulance",
                "breathing_issues": "emergency medical services",
                "head_trauma": "emergency department",
                "burns": "burn unit/emergency services"
            }
        } 