from typing import Dict, List, Any, Tuple, Union
from .base_agent import BaseAgent
from ..utils.keyword_extractor import contains_keywords

class PregnancyAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Pregnancy Expert",
            expertise=[
                # English keywords
                "pregnancy", "trimester", "prenatal", "morning sickness", "ultrasound",
                "baby", "stroller", "car seat", "crib", "nursery",
                # Hebrew keywords
                "הריון", "טרימסטר", "בחילות", "אולטרסאונד",
                "תינוק", "עגלה", "עגלת", "כיסא", "מיטת תינוק", "חדר תינוק"
            ],
            llm_service=llm_service
        )
        self.medical_disclaimer = ("\n\nPlease note: This information is for general guidance only. "
                                 "Always consult with your healthcare provider for medical advice.")
        
    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Pregnancy confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _calculate_confidence(self, query: str, keywords: List[str]) -> float:
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        # Count matching keywords, including partial matches for Hebrew
        matching_keywords = sum(1 for keyword in self.expertise 
                              if keyword.lower() in query_lower or 
                              any(word in query_lower for word in keyword.lower().split()))
        return min(matching_keywords / 2, 1.0)  # Normalize confidence score

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a pregnancy expert, analyze and respond to: {query}

              Follow these guidelines:
              1. Trimester-specific information if applicable
              2. Common symptoms and normal variations
              3. Warning signs that need medical attention
              4. Evidence-based recommendations
              5. Lifestyle and self-care tips
              6. Preparation steps for upcoming stages
              
              Important:
              - Be specific to the stage of pregnancy if mentioned
              - Include both physical and emotional aspects
              - Emphasize safety precautions when relevant
              - Acknowledge normal variations in pregnancy experiences
              
              Medical Disclaimer: Always consult healthcare providers for medical decisions.
              Respond in the same language as the question."""

    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict:
        try:
            response = await super().process_query(query, context)
            # Should return response directly without wrapping
            return response
        except Exception as e:
            print(f"Error in PregnancyAgent: {str(e)}")
            raise

    def _format_context(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return None
            
        context_str = "Previous conversation:\n"
        for msg in reversed(history):
            context_str += f"Q: {msg['query']}\nA: {msg['response']}\n\n"
        return context_str

    def _get_base_response(self, query: str) -> str:
        query_lower = query.lower()
        if "morning sickness" in query_lower:
            return ("Morning sickness is common during the first trimester. "
                   "Try eating small, frequent meals and staying hydrated. "
                   "Some find ginger tea or crackers helpful.")
        elif "ultrasound" in query_lower:
            return ("Typically, the first ultrasound is performed between "
                   "weeks 8-14 of pregnancy. Additional scans may be scheduled "
                   "based on your specific needs and pregnancy progression.")
        return "I can help you with pregnancy-related questions. Please be more specific."

    def _is_medical_advice(self, query: str) -> bool:
        medical_keywords = {"safe", "normal", "risk", "danger", "medicine", "medication"}
        return any(keyword in query.lower() for keyword in medical_keywords)

    def _enhance_with_context(self, response: str, context: List[Dict[str, Any]]) -> str:
        # Add relevant information from recent conversation
        # This is a simplified version - you'd want more sophisticated context handling
        return response 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "general pregnancy information",
                "common symptom guidance",
                "lifestyle recommendations",
                "nutrition suggestions",
                "exercise guidelines",
                "comfort measures"
            ],
            "cannot_do": [
                "medical diagnosis",
                "medication advice",
                "emergency situation handling",
                "specific medical treatment",
                "ultrasound interpretation",
                "test result analysis"
            ],
            "refer_to": {
                "medical_concerns": "obstetrician/healthcare provider",
                "complications": "emergency medical services",
                "mental_health": "mental health professional",
                "nutrition_plans": "registered dietitian",
                "exercise_programs": "prenatal fitness specialist",
                "high_risk": "maternal-fetal medicine specialist"
            }
        } 