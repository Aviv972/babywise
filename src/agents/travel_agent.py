from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class TravelAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Baby Travel Expert",
            expertise=[
                # English keywords
                "travel", "flight", "car", "trip", "vacation", "journey",
                "packing", "airplane", "hotel", "transportation", "abroad",
                "passport", "documents", "luggage", "accommodation",
                # Hebrew keywords
                "נסיעה", "טיסה", "רכב", "טיול", "חופשה", "מסע",
                "אריזה", "מטוס", "מלון", "תחבורה", "חול",
                "דרכון", "מסמכים", "מזוודה", "לינה"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "destination",
            "travel_duration",
            "transport_method",
            "accommodation_type"
        ]
        
        # Travel type specific questions
        self.context_questions_map = {
            "flight": [
                "flight_duration",
                "layovers",
                "seat_assignment",
                "airline_policies",
                "timezone_changes"
            ],
            "car": [
                "journey_length",
                "car_seat_type",
                "planned_stops",
                "vehicle_space",
                "climate_control"
            ],
            "hotel": [
                "room_type",
                "baby_facilities",
                "crib_availability",
                "kitchen_access",
                "nearby_amenities"
            ],
            "international": [
                "passport_status",
                "vaccination_requirements",
                "medical_facilities",
                "language_barriers",
                "local_baby_supplies"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a baby travel expert, provide guidance about: {query}

              Analysis Framework:
              1. Travel Planning
                 - Pre-trip preparations
                 - Documentation needs
                 - Timing considerations
                 - Route planning
              
              2. Essential Packing
                 - Must-have items
                 - Medical supplies
                 - Food and feeding
                 - Emergency kit
              
              3. Transportation Tips
                 - Mode-specific advice
                 - Safety measures
                 - Comfort strategies
                 - Timing and breaks
              
              4. Accommodation Needs
                 - Baby-friendly features
                 - Safety considerations
                 - Essential amenities
                 - Location factors
              
              5. Daily Management
                 - Schedule adaptation
                 - Sleep arrangements
                 - Feeding solutions
                 - Health precautions
              
              Respond in the same language as the question.""" 

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Travel confidence for '{query}': {confidence}")
        return confidence > 0.2 

    def _identify_travel_type(self, query: str) -> Optional[str]:
        travel_keywords = {
            "flight": ["fly", "plane", "airport", "טיסה", "מטוס", "שדה תעופה"],
            "car": ["drive", "road trip", "car", "נסיעה", "רכב", "טיול"],
            "hotel": ["stay", "hotel", "room", "מלון", "חדר", "לינה"],
            "international": ["abroad", "overseas", "country", "חול", "חוץ לארץ", "מדינה"]
        }
        
        query_lower = query.lower()
        for ttype, keywords in travel_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return ttype
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "travel planning tips",
                "packing suggestions",
                "transportation advice",
                "accommodation guidance",
                "baby-friendly destinations",
                "travel safety tips"
            ],
            "cannot_do": [
                "medical travel clearance",
                "vaccination recommendations",
                "insurance coverage advice",
                "visa/legal requirements",
                "emergency medical planning",
                "airline policy guarantees"
            ],
            "refer_to": {
                "medical_clearance": "pediatrician",
                "vaccinations": "travel clinic",
                "insurance": "insurance provider",
                "legal_requirements": "embassy/consulate",
                "airline_policies": "specific airline",
                "emergency_planning": "travel medicine specialist"
            }
        } 