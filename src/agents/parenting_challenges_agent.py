from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class ParentingChallengesAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Parenting Challenges Expert",
            expertise=[
                # English keywords
                "crying", "fussy", "colicky", "tantrum", "behavior", "stress",
                "overwhelmed", "time management", "organization", "routine",
                "development", "milestone", "adjustment", "siblings", "balance",
                # Hebrew keywords
                "בכי", "רגזנות", "קוליק", "התקף זעם", "התנהגות", "לחץ",
                "עומס", "ניהול זמן", "ארגון", "שגרה", "התפתחות",
                "אבן דרך", "הסתגלות", "אחים", "איזון"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "age",
            "behavior_duration",
            "trigger_patterns",
            "previous_approaches",
            "family_dynamics"
        ]
        
        # Challenge type specific questions
        self.context_questions_map = {
            "sleep": [
                "sleep_environment",
                "bedtime_routine",
                "night_wakings",
                "daytime_schedule",
                "recent_changes"
            ],
            "behavior": [
                "specific_behaviors",
                "trigger_situations",
                "current_responses",
                "consistency_level",
                "developmental_stage"
            ],
            "eating": [
                "food_preferences",
                "mealtime_routine",
                "eating_environment",
                "food_reactions",
                "nutritional_concerns"
            ],
            "siblings": [
                "age_differences",
                "interaction_patterns",
                "jealousy_signs",
                "attention_division",
                "individual_needs"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a parenting challenges expert, analyze and address: {query}

              Analysis Framework:
              1. Situation Assessment
                 - Age-specific behavior
                 - Developmental stage
                 - Environmental factors
                 - Trigger identification
                 - Pattern recognition
              
              2. Immediate Response
                 - De-escalation techniques
                 - Safety measures
                 - Communication strategies
                 - Emergency procedures
                 - Temporary solutions
              
              3. Long-term Strategy
                 - Behavioral understanding
                 - Prevention methods
                 - Routine adjustments
                 - Consistency planning
                 - Progress tracking
              
              4. Family Dynamics
                 - Parent cooperation
                 - Sibling involvement
                 - Support system
                 - Work-life balance
                 - Family routines
              
              5. Parent Support
                 - Self-care strategies
                 - Stress management
                 - Resource identification
                 - Professional help indicators
                 - Community support
              
              Key Considerations:
              - Respect individual differences
              - Consider family values
              - Maintain realistic expectations
              - Focus on positive reinforcement
              - Build consistent approaches
              
              Note: For serious behavioral or emotional concerns, seek professional guidance.
              Respond in the same language as the question."""

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Parenting challenges confidence for '{query}': {confidence}")
        return confidence > 0.2 

    def _identify_challenge_type(self, query: str) -> Optional[str]:
        challenge_keywords = {
            "sleep": ["sleep", "bedtime", "night", "שינה", "לילה", "הרדמות"],
            "behavior": ["tantrum", "crying", "behavior", "התקף", "בכי", "התנהגות"],
            "eating": ["eat", "food", "meal", "אוכל", "ארוחה", "אכילה"],
            "siblings": ["sibling", "brother", "sister", "אח", "אחות", "אחים"]
        }
        
        query_lower = query.lower()
        for ctype, keywords in challenge_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return ctype
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "behavior management tips",
                "routine establishment",
                "positive parenting strategies",
                "common challenge solutions",
                "developmental guidance",
                "family dynamic advice"
            ],
            "cannot_do": [
                "behavioral disorder diagnosis",
                "trauma counseling",
                "family therapy",
                "custody advice",
                "legal parenting issues",
                "mental health treatment"
            ],
            "refer_to": {
                "behavioral_disorders": "child psychologist",
                "family_conflict": "family therapist",
                "legal_issues": "family lawyer",
                "abuse_concerns": "child protection services",
                "mental_health": "mental health professional",
                "school_issues": "educational consultant"
            }
        } 