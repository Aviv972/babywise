from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class HygieneAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Hygiene Expert",
            expertise=[
                # English keywords
                "diaper", "diapering", "bath", "bathing", "hygiene", "rash",
                "wipes", "changing", "skincare", "baby soap", "lotion", "powder",
                "cleaning", "grooming", "nails", "cradle cap", "washing",
                # Hebrew keywords
                "חיתול", "החתלה", "אמבטיה", "רחצה", "היגיינה", "פריחה",
                "מגבונים", "החלפה", "טיפוח", "סבון תינוקות", "קרם", "טלק",
                "ניקיון", "טיפוח", "ציפורניים", "גזזת", "שטיפה"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "skin_type",
            "current_routine",
            "problem_areas",
            "product_sensitivities"
        ]
        
        # Care type specific questions
        self.context_questions_map = {
            "bathing": [
                "water_temperature",
                "bath_frequency",
                "skin_reactions",
                "current_products",
                "bath_time_routine"
            ],
            "diapering": [
                "diaper_type",
                "change_frequency",
                "rash_history",
                "current_products",
                "skin_sensitivity"
            ],
            "skincare": [
                "skin_condition",
                "problem_areas",
                "current_products",
                "allergies",
                "weather_effects"
            ],
            "oral": [
                "teeth_status",
                "cleaning_routine",
                "products_used",
                "gum_health",
                "feeding_habits"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a baby hygiene and care expert, provide detailed guidance about: {query}

              Analysis Framework:
              1. Daily Care Routine
                 - Step-by-step procedures
                 - Frequency recommendations
                 - Age-specific considerations
                 - Best practices
              
              2. Diapering
                 - Proper technique
                 - Rash prevention
                 - Product selection
                 - Change frequency
                 - Warning signs
              
              3. Bathing & Skincare
                 - Bath safety measures
                 - Water temperature
                 - Product recommendations
                 - Skin condition monitoring
                 - Special care areas
              
              4. Health & Safety
                 - Hygiene best practices
                 - Infection prevention
                 - Environmental factors
                 - When to seek medical help
                 - Emergency situations
              
              5. Equipment & Supplies
                 - Essential items
                 - Product safety
                 - Storage requirements
                 - Travel considerations
                 - Cost-effective options
              
              Important Guidelines:
              - Prioritize baby's comfort
              - Maintain proper sanitation
              - Monitor skin reactions
              - Follow safety protocols
              - Consider environmental impact
              
              Medical Note: For persistent skin issues or health concerns, consult a healthcare provider.
              Respond in the same language as the question."""

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Hygiene confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _identify_care_type(self, query: str) -> Optional[str]:
        care_keywords = {
            "bathing": ["bath", "wash", "clean", "אמבטיה", "רחצה", "ניקיון"],
            "diapering": ["diaper", "change", "rash", "חיתול", "החלפה", "תפרחת"],
            "skincare": ["skin", "cream", "lotion", "עור", "קרם", "תחליב"],
            "oral": ["teeth", "gums", "mouth", "שיניים", "חניכיים", "פה"]
        }
        
        query_lower = query.lower()
        for ctype, keywords in care_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return ctype
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "basic hygiene guidance",
                "bathing instructions",
                "diapering tips",
                "skincare routines",
                "oral care basics",
                "grooming advice"
            ],
            "cannot_do": [
                "medical skin conditions",
                "infection treatment",
                "medication recommendations",
                "dental procedures",
                "medical diagnoses",
                "prescription advice"
            ],
            "refer_to": {
                "skin_conditions": "pediatrician/dermatologist",
                "infections": "healthcare provider",
                "dental_issues": "pediatric dentist",
                "severe_rashes": "dermatologist",
                "oral_problems": "pediatric dentist",
                "persistent_issues": "healthcare provider"
            }
        } 