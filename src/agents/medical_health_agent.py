from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class MedicalHealthAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Medical and Health Expert",
            expertise=[
                # English keywords
                "fever", "cold", "cough", "rash", "temperature", "sick",
                "medicine", "vaccination", "symptoms", "health", "doctor",
                "emergency", "infection", "allergy", "pain", "treatment",
                # Hebrew keywords
                "חום", "הצטננות", "שיעול", "פריחה", "טמפרטורה", "חולה",
                "תרופה", "חיסון", "תסמינים", "בריאות", "רופא",
                "חירום", "דלקת", "אלרגיה", "כאב", "טיפול"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "symptoms_duration",
            "temperature",
            "eating_drinking",
            "medication_history"
        ]
        
        # Condition-specific questions
        self.context_questions_map = {
            "fever": [
                "age",
                "temperature",
                "duration",
                "eating_drinking",
                "other_symptoms"
            ],
            "rash": [
                "age",
                "location_on_body",
                "appearance",
                "duration",
                "recent_changes"
            ],
            "cough": [
                "age",
                "duration",
                "type_of_cough",
                "sleep_impact",
                "breathing_difficulty"
            ]
        }

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Medical confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a pediatric health expert, provide guidance about: {query}

              Analysis Framework:
              1. Symptom Assessment
                 - Common symptoms
                 - Duration and severity
                 - Normal vs concerning signs
                 - Age-specific considerations
              
              2. Basic Care Guidelines
                 - Home care measures
                 - Comfort techniques
                 - Prevention strategies
                 - Hygiene practices
              
              3. Warning Signs
                 - Red flags to watch
                 - Emergency indicators
                 - When to seek help
                 - What to monitor
              
              4. Recovery Support
                 - Rest requirements
                 - Feeding/hydration
                 - Environmental factors
                 - Follow-up care
              
              IMPORTANT MEDICAL DISCLAIMER:
              This advice is for informational purposes only.
              Always consult a healthcare provider for:
              - Specific medical advice
              - Diagnosis and treatment
              - Emergency situations
              - Persistent symptoms
              
              Respond in the same language as the question.""" 

    def _identify_condition(self, query: str) -> Optional[str]:
        condition_keywords = {
            "fever": ["fever", "temperature", "hot", "חום", "חמים"],
            "rash": ["rash", "skin", "irritation", "פריחה", "עור"],
            "cough": ["cough", "breathing", "chest", "שיעול", "נשימה"]
        }
        
        query_lower = query.lower()
        for condition, keywords in condition_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return condition
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "basic health advice",
                "common symptoms",
                "first aid guidance",
                "preventive care",
                "when to seek medical help"
            ],
            "cannot_do": [
                "diagnose conditions",
                "prescribe medication",
                "modify existing treatment",
                "emergency medical advice",
                "specific medical procedures"
            ],
            "refer_to": {
                "diagnosis": "healthcare provider",
                "medication": "pediatrician",
                "emergency": "emergency services (call emergency number)",
                "treatment": "healthcare provider",
                "mental_health": "mental health professional"
            }
        } 