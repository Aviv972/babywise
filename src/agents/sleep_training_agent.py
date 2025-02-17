from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from src.constants import AgentTypes

class SleepTrainingAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.SLEEP_TRAINING
        self.name = "Sleep Training Expert"
        self.expertise = [
            # English keywords
            "sleep training", "cry it out", "ferber", "gentle sleep", "self soothe",
            "bedtime routine", "sleep schedule", "night weaning", "sleep regression",
            "sleep habits", "sleep cues", "drowsy but awake",
            # Hebrew keywords
            "אימון שינה", "בכי מבוקר", "פרבר", "שינה עדינה", "הרגעה עצמית",
            "שגרת שינה", "לוח זמני שינה", "גמילה מהנקת לילה", "רגרסיית שינה",
            "הרגלי שינה", "סימני עייפות", "עייף אך ער"
        ]
        self.required_context = [
            "baby_age",
            "current_sleep_pattern",
            "sleep_environment",
            "feeding_pattern",
            "sleep_training_history",
            "preferred_method",
            "parent_comfort_level"
        ]
        self._set_role_boundaries()

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process sleep training specific query"""
        # Get missing critical fields
        missing_fields = self._get_missing_critical_fields(context)
        
        if missing_fields:
            # If we're missing critical information, ask a follow-up question
            field = missing_fields[0]  # Ask for the first missing field
            return {
                'type': 'follow_up_question',
                'field': field,
                'question': self._generate_context_question(field)
            }
        
        # If we have all critical information, generate a response using the prompt
        return await self.llm_service.generate_response(
            self._prepare_prompt(query),
            context=context,
            chat_history=chat_history
        )

    def _generate_context_question(self, field: str) -> str:
        """Generate a context-gathering question for the specified field"""
        questions = {
            "baby_age": "How old is your baby?",
            "current_sleep_pattern": "What is your baby's current sleep schedule and wake patterns?",
            "sleep_environment": "Can you describe your baby's sleep environment? (room temperature, lighting, noise level, etc.)",
            "feeding_pattern": "What is your baby's current feeding schedule, especially for night feedings?",
            "sleep_training_history": "Have you tried any sleep training methods before? If so, what was your experience?",
            "preferred_method": "Do you have a preference for sleep training method (e.g., gradual/gentle, Ferber, cry-it-out)?",
            "parent_comfort_level": "How comfortable are you with letting your baby cry for short periods?"
        }
        return questions.get(field, f"Could you tell me about your baby's {field.replace('_', ' ')}?")

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a sleep training expert, analyze and respond to: {query}

                  Analysis Framework:
                  1. Sleep Training Assessment
                     - Age-appropriate methods
                     - Current sleep patterns
                     - Parent comfort level
                     - Previous attempts
                  
                  2. Method Selection
                     - Recommended approach
                     - Alternative options
                     - Customization needs
                     - Implementation timeline
                  
                  3. Implementation Strategy
                     - Step-by-step plan
                     - Expected challenges
                     - Progress markers
                     - Adjustment guidelines
                  
                  4. Support Framework
                     - Partner involvement
                     - Consistency tips
                     - Troubleshooting guide
                     - When to adjust
                  
                  5. Success Metrics
                     - Expected timeline
                     - Progress indicators
                     - Common setbacks
                     - When to seek help
                  
                  Important Considerations:
                  - Respect parental comfort level
                  - Consider family dynamics
                  - Maintain safety focus
                  - Support emotional needs
                  
                  Respond in the same language as the question."""

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "sleep training methods",
                "bedtime routines",
                "sleep environment tips",
                "age-appropriate schedules",
                "common sleep issues",
                "gentle sleep solutions"
            ],
            "cannot_do": [
                "sleep disorder diagnosis",
                "medical sleep problems",
                "medication advice",
                "psychiatric issues",
                "breathing problems",
                "serious sleep conditions"
            ],
            "refer_to": {
                "sleep_disorders": "pediatric sleep specialist",
                "medical_issues": "pediatrician",
                "breathing_problems": "sleep clinic",
                "behavioral_concerns": "child psychologist",
                "anxiety_issues": "mental health professional",
                "persistent_problems": "sleep consultant"
            }
        } 