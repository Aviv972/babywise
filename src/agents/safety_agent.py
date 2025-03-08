from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class SafetyAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Safety Expert",
            expertise=[
                # English keywords
                "safety", "baby-proofing", "childproof", "hazard", "danger",
                "protection", "secure", "prevention", "accident", "emergency",
                "first aid", "monitor", "gate", "lock", "cover", "guard",
                # Hebrew keywords
                "בטיחות", "התאמה לתינוק", "מוגן ילדים", "סכנה", "הגנה",
                "אבטחה", "מניעה", "תאונה", "חירום", "עזרה ראשונה",
                "מעקב", "שער", "מנעול", "כיסוי", "משמר"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "child_age",
            "home_environment",
            "mobility_level",
            "specific_concerns",
            "existing_measures"
        ]
        
        # Safety area specific questions
        self.context_questions_map = {
            "home": [
                "living_space",
                "hazard_areas",
                "existing_safety_measures",
                "child_access_areas",
                "supervision_level"
            ],
            "sleep": [
                "sleep_environment",
                "bedding_type",
                "room_temperature",
                "monitoring_method",
                "sleep_position"
            ],
            "products": [
                "product_type",
                "age_range",
                "safety_standards",
                "usage_frequency",
                "maintenance_needs"
            ],
            "outdoors": [
                "activity_type",
                "location_safety",
                "weather_conditions",
                "supervision_plan",
                "emergency_access"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a baby safety expert, provide comprehensive safety guidance about: {query}

              Analysis Framework:
              1. Risk Assessment
                 - Immediate hazards
                 - Potential risks
                 - Age-specific concerns
                 - Environmental factors
                 - Common accidents
              
              2. Prevention Strategy
                 - Safety equipment
                 - Childproofing methods
                 - Supervision requirements
                 - Emergency preparations
                 - Safety routines
              
              3. Home Safety
                 - Room-by-room assessment
                 - Furniture securing
                 - Electrical safety
                 - Chemical storage
                 - Fall prevention
              
              4. Product Safety
                 - Safety standards
                 - Age recommendations
                 - Installation requirements
                 - Maintenance needs
                 - Recall checks
              
              5. Emergency Preparedness
                 - First aid essentials
                 - Emergency contacts
                 - Action plans
                 - CPR/choking response
                 - Medical information
              
              Critical Guidelines:
              - Follow all safety standards
              - Regular safety checks
              - Update measures with growth
              - Document emergency info
              - Train all caregivers
              
              Important: Always follow manufacturer guidelines and local safety regulations.
              Respond in the same language as the question."""

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Safety confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _identify_safety_area(self, query: str) -> Optional[str]:
        area_keywords = {
            "home": ["home", "house", "room", "בית", "חדר", "דירה"],
            "sleep": ["sleep", "crib", "bed", "שינה", "מיטה", "עריסה"],
            "products": ["product", "toy", "gear", "מוצר", "צעצוע", "ציוד"],
            "outdoors": ["outside", "park", "playground", "חוץ", "פארק", "גן שעשועים"]
        }
        
        query_lower = query.lower()
        for area, keywords in area_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return area
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "safety guidelines",
                "childproofing advice",
                "product safety information",
                "preventive measures",
                "risk assessment"
            ],
            "cannot_do": [
                "product repair instructions",
                "medical emergency procedures",
                "legal safety requirements",
                "product safety certification",
                "structural home modifications"
            ],
            "refer_to": {
                "repairs": "qualified technician",
                "emergency": "emergency services",
                "legal": "relevant authorities",
                "construction": "licensed contractor",
                "product_defects": "manufacturer"
            }
        } 