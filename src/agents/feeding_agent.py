from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class FeedingAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Feeding and Nutrition Expert",
            expertise=[
                # English keywords
                "feeding", "breastfeeding", "formula", "solids", "weaning",
                "bottle feeding", "nursing", "food introduction", "feeding schedule",
                "milk supply", "pumping", "storing milk", "baby food", "nutrition",
                # Hebrew keywords
                "האכלה", "הנקה", "פורמולה", "מוצקים", "גמילה",
                "האכלה בבקבוק", "שאיבת חלב", "מזון תינוקות", "לוח האכלה",
                "אספקת חלב", "שאיבה", "אחסון חלב", "מזון לתינוק", "תזונה"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "feeding_type",  # breast/bottle/solids
            "feeding_schedule",
            "allergies",
            "current_issues"
        ]
        
        # Feeding-type specific questions
        self.context_questions_map = {
            "breastfeeding": [
                "age",
                "feeding_frequency",
                "latch_issues",
                "milk_supply",
                "pumping_schedule"
            ],
            "formula": [
                "age",
                "formula_type",
                "amount_per_feed",
                "feeding_schedule",
                "mixing_method"
            ],
            "solids": [
                "age",
                "current_foods",
                "texture_preferences",
                "allergies",
                "meal_schedule"
            ],
            "weaning": [
                "age",
                "current_routine",
                "preferred_foods",
                "feeding_skills",
                "transition_progress"
            ]
        }

        self.context_questions = {}

    def _generate_context_question(self, field: str) -> str:
        questions = {
            "age": "מה הגיל של התינוק? / How old is your baby?",
            "feeding_type": "איך התינוק ניזון כרגע? (הנקה/בקבוק/מוצקים) / How is your baby currently fed? (breast/bottle/solids)",
            "feeding_schedule": "מה לוח הזמנים הנוכחי של ההאכלות? / What is your current feeding schedule?",
            "allergies": "האם ידוע על אלרגיות? / Are there any known allergies?",
            "current_issues": "האם יש בעיות או אתגרים ספציפיים? / Are there any specific issues or challenges?"
        }
        return questions.get(field, f"אנא ספרו לנו על {field} / Please tell us about {field}")

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Feeding confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _identify_feeding_type(self, query: str) -> Optional[str]:
        feeding_keywords = {
            "breastfeeding": ["breast", "nursing", "latch", "milk supply", "הנקה", "חלב אם"],
            "formula": ["formula", "bottle", "mix", "תמ״ל", "פורמולה", "בקבוק"],
            "solids": ["solid", "food", "puree", "מוצק", "אוכל", "מחית"],
            "weaning": ["wean", "stop nursing", "גמילה", "להפסיק הנקה"]
        }
        
        query_lower = query.lower()
        for ftype, keywords in feeding_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return ftype
        return None

    def _prepare_prompt(self, query: str) -> str:
        # Identify feeding type and set appropriate context questions
        feeding_type = self._identify_feeding_type(query)
        if feeding_type in self.context_questions_map:
            self.required_context = self.context_questions_map[feeding_type]
            
        return f"""As a feeding and nutrition expert, provide comprehensive guidance about: {query}

                  Analysis Framework:
                  1. Feeding Assessment
                     - Age/stage appropriate feeding
                     - Current feeding method
                     - Nutritional needs
                     - Feeding cues
                  
                  2. Method-Specific Guidance
                     Breastfeeding:
                     - Positioning and latch
                     - Supply management
                     - Common challenges
                     - Pumping/storage
                     
                     Formula Feeding:
                     - Preparation safety
                     - Formula selection
                     - Feeding schedule
                     - Equipment sterilization
                     
                     Solid Foods:
                     - Introduction timing
                     - Food progression
                     - Texture management
                     - Allergen introduction
                  
                  3. Safety & Hygiene
                     - Safe feeding practices
                     - Food safety guidelines
                     - Equipment cleaning
                     - Storage requirements
                  
                  4. Problem-Solving
                     - Common feeding issues
                     - Warning signs
                     - Growth considerations
                     - When to seek help
                  
                  5. Practical Implementation
                     - Step-by-step guidance
                     - Schedule suggestions
                     - Equipment needs
                     - Travel considerations
                  
                  Important Notes:
                  - Always prioritize safety
                  - Consider family circumstances
                  - Respect feeding choices
                  - Monitor baby's cues
                  
                  Medical Disclaimer: Consult healthcare providers for medical concerns.
                  Respond in the same language as the question."""

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "feeding techniques",
                "nutrition guidance",
                "feeding schedules",
                "food introduction tips",
                "common feeding issues",
                "equipment recommendations"
            ],
            "cannot_do": [
                "medical nutrition therapy",
                "allergy diagnosis",
                "eating disorder treatment",
                "medical condition diets",
                "medication interactions"
            ],
            "refer_to": {
                "allergies": "pediatric allergist",
                "medical_diet": "pediatric nutritionist",
                "eating_disorders": "healthcare provider",
                "growth_issues": "pediatrician",
                "swallowing_problems": "feeding specialist"
            }
        } 