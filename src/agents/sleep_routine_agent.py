from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class SleepRoutineAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Sleep Routine Expert",
            expertise=[
                # English keywords
                "sleep", "routine", "schedule", "nap", "bedtime", "wake up",
                "sleep training", "daily schedule", "night feeding", "sleep regression",
                "sleep habits", "tired signs", "settling", "self-soothing",
                # Hebrew keywords
                "שינה", "שגרה", "לוח זמנים", "נמנום", "זמן שינה", "התעוררות",
                "אימון שינה", "סדר יום", "האכלת לילה", "רגרסיית שינה",
                "הרגלי שינה", "סימני עייפות", "הרגעה", "הרגעה עצמית"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "current_schedule",
            "sleep_environment",
            "feeding_pattern",
            "sleep_training_history"
        ]
        
        # Age-specific questions
        self.context_questions_map = {
            "newborn": [
                "feeding_frequency",
                "day_night_confusion",
                "sleeping_location",
                "swaddle_preference"
            ],
            "infant": [
                "nap_schedule",
                "bedtime_routine",
                "sleep_associations",
                "night_wakings"
            ],
            "toddler": [
                "bedtime_resistance",
                "room_sharing",
                "nap_transitions",
                "night_terrors"
            ]
        }

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Sleep routine confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a sleep and routine expert, analyze and respond to: {query}

                  Analysis Framework:
                  1. Sleep Assessment
                     - Age-specific sleep needs
                     - Current sleep patterns
                     - Sleep environment factors
                     - Signs of sleep readiness
                  
                  2. Routine Development
                     - Schedule recommendations
                     - Wake windows
                     - Nap transitions
                     - Bedtime sequence
                  
                  3. Problem Solving
                     - Common sleep challenges
                     - Developmental considerations
                     - Sleep regressions
                     - Night wakings
                  
                  4. Implementation Strategy
                     - Step-by-step approach
                     - Gradual changes
                     - Consistency tips
                     - Progress tracking
                  
                  5. Parent Support
                     - Managing expectations
                     - Self-care strategies
                     - Partner involvement
                     - When to seek help
                  
                  Important Considerations:
                  - Adapt advice to family circumstances
                  - Consider cultural preferences
                  - Acknowledge different parenting styles
                  - Emphasize safety guidelines
                  
                  Respond in the same language as the question.""" 

    def _identify_age_group(self, query: str) -> Optional[str]:
        age_keywords = {
            "newborn": ["newborn", "0-3 months", "יילוד", "0-3 חודשים"],
            "infant": ["infant", "3-12 months", "תינוק", "3-12 חודשים"],
            "toddler": ["toddler", "1-3 years", "פעוט", "1-3 שנים"]
        }
        
        query_lower = query.lower()
        for age_group, keywords in age_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return age_group
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "sleep schedule advice",
                "routine development",
                "sleep environment tips",
                "settling techniques",
                "age-appropriate patterns",
                "common sleep issues"
            ],
            "cannot_do": [
                "sleep disorder diagnosis",
                "medication advice",
                "medical condition treatment",
                "breathing issue guidance",
                "psychiatric sleep problems"
            ],
            "refer_to": {
                "sleep_disorders": "pediatric sleep specialist",
                "breathing": "pediatrician",
                "medical_conditions": "healthcare provider",
                "mental_health": "child psychologist",
                "persistent_issues": "sleep consultant"
            }
        } 