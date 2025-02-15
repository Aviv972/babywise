from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class EducationAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Early Education Expert",
            expertise=[
                # English keywords
                "learning", "education", "development", "play", "activities",
                "reading", "games", "stimulation", "skills", "cognitive",
                "memory", "attention", "creativity", "music", "art",
                "numbers", "colors", "shapes", "language", "social",
                # Hebrew keywords
                "למידה", "חינוך", "התפתחות", "משחק", "פעילויות",
                "קריאה", "משחקים", "גירוי", "כישורים", "קוגניטיבי",
                "זיכרון", "קשב", "יצירתיות", "מוזיקה", "אומנות",
                "מספרים", "צבעים", "צורות", "שפה", "חברתי"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "current_interests",
            "attention_span",
            "learning_style",
            "previous_activities"
        ]
        
        # Activity type specific questions
        self.context_questions_map = {
            "reading": [
                "age",
                "favorite_books",
                "attention_span",
                "language_exposure",
                "bedtime_routine"
            ],
            "music": [
                "age",
                "musical_exposure",
                "favorite_songs",
                "movement_ability",
                "instrument_interest"
            ],
            "art": [
                "age",
                "fine_motor_skills",
                "color_recognition",
                "preferred_materials",
                "creative_interests"
            ],
            "sensory": [
                "age",
                "sensory_preferences",
                "texture_tolerance",
                "previous_experiences",
                "environmental_setup"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As an early education expert, provide guidance about: {query}

              Analysis Framework:
              1. Learning Assessment
                 - Age-appropriate activities
                 - Developmental stage
                 - Learning style
                 - Current abilities
              
              2. Educational Approach
                 - Play-based learning
                 - Structured activities
                 - Interactive methods
                 - Sensory experiences
              
              3. Skill Development
                 - Cognitive skills
                 - Motor skills
                 - Social skills
                 - Language development
                 - Problem-solving
              
              4. Activity Planning
                 - Daily routines
                 - Educational games
                 - Creative projects
                 - Learning materials
              
              5. Progress Support
                 - Observation methods
                 - Milestone tracking
                 - Encouragement strategies
                 - Parent involvement
              
              Key Principles:
              - Follow child's interests
              - Make learning fun
              - Build on successes
              - Maintain patience
              - Celebrate progress
              
              Respond in the same language as the question.""" 

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Education confidence for '{query}': {confidence}")
        return confidence > 0.2 

    def _identify_activity_type(self, query: str) -> Optional[str]:
        activity_keywords = {
            "reading": ["book", "story", "read", "ספר", "סיפור", "קריאה"],
            "music": ["song", "music", "sing", "שיר", "מוזיקה", "לשיר"],
            "art": ["draw", "paint", "craft", "לצייר", "לצבוע", "יצירה"],
            "sensory": ["touch", "feel", "texture", "מגע", "תחושה", "מרקם"]
        }
        
        query_lower = query.lower()
        for atype, keywords in activity_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return atype
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "learning activity suggestions",
                "age-appropriate education",
                "play-based learning tips",
                "educational material advice",
                "developmental play ideas",
                "learning environment setup"
            ],
            "cannot_do": [
                "learning disability diagnosis",
                "special education plans",
                "therapeutic interventions",
                "psychological assessments",
                "academic performance evaluation",
                "curriculum development"
            ],
            "refer_to": {
                "learning_disabilities": "educational psychologist",
                "special_needs": "special education specialist",
                "academic_issues": "educational consultant",
                "behavioral_concerns": "child psychologist",
                "speech_issues": "speech therapist",
                "development_delays": "developmental specialist"
            }
        } 