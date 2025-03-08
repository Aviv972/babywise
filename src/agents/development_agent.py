from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class DevelopmentAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Development Expert",
            expertise=[
                # English keywords
                "milestone", "development", "growth", "skill", "learning",
                "crawling", "walking", "talking", "teething", "motor skills",
                # Hebrew keywords
                "התפתחות", "אבן דרך", "גדילה", "כישורים", "למידה",
                "זחילה", "הליכה", "דיבור", "שיניים", "מוטוריקה"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "current_abilities",
            "recent_changes",
            "concerns",
            "family_history"
        ]
        
        # Development area specific questions
        self.context_questions_map = {
            "motor": [
                "age",
                "current_movements",
                "preferred_position",
                "physical_activity",
                "equipment_used"
            ],
            "language": [
                "age",
                "sounds_made",
                "words_used",
                "languages_exposed",
                "communication_methods"
            ],
            "social": [
                "age",
                "interaction_level",
                "play_preferences",
                "social_exposure",
                "emotional_responses"
            ],
            "cognitive": [
                "age",
                "attention_span",
                "problem_solving",
                "memory_skills",
                "learning_interests"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a child development expert, analyze and advise about: {query}

              Analysis Framework:
              1. Developmental Stage
                 - Age-appropriate milestones
                 - Normal variations
                 - Next expected developments
                 - Red flags to watch for
              
              2. Skill Assessment
                 - Physical development
                 - Cognitive development
                 - Social/emotional development
                 - Language development
                 - Fine/gross motor skills
              
              3. Support Strategies
                 - Activities to encourage
                 - Environmental setup
                 - Play suggestions
                 - Learning opportunities
              
              4. Progress Monitoring
                 - What to observe
                 - When to expect changes
                 - How to document
                 - When to seek help
              
              Important Notes:
              - Every child develops differently
              - Consider individual factors
              - Focus on overall progress
              - Celebrate small achievements
              
              Medical Note: For developmental concerns, consult healthcare provider.
              Respond in the same language as the question.""" 

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Development confidence for '{query}': {confidence}")
        return confidence > 0.2 

    def _identify_development_area(self, query: str) -> Optional[str]:
        area_keywords = {
            "motor": ["crawl", "walk", "move", "physical", "זחילה", "הליכה", "תנועה"],
            "language": ["talk", "word", "speech", "language", "דיבור", "מילה", "שפה"],
            "social": ["smile", "play", "social", "friend", "חיוך", "משחק", "חברתי"],
            "cognitive": ["learn", "understand", "think", "memory", "למידה", "הבנה", "זיכרון"]
        }
        
        query_lower = query.lower()
        for area, keywords in area_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return area
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "milestone information",
                "developmental activities",
                "age-appropriate expectations",
                "skill-building suggestions",
                "progress monitoring tips"
            ],
            "cannot_do": [
                "developmental diagnosis",
                "therapy recommendations",
                "medical assessments",
                "disability evaluations",
                "treatment plans"
            ],
            "refer_to": {
                "delays": "developmental pediatrician",
                "speech": "speech therapist",
                "motor_skills": "occupational therapist",
                "behavior": "child psychologist",
                "learning_issues": "educational specialist"
            }
        } 