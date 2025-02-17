from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from src.constants import AgentTypes

class BreastfeedingAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.BREASTFEEDING
        self.name = "Breastfeeding Expert"
        self.expertise = [
            # English keywords
            "breastfeeding", "nursing", "lactation", "milk supply",
            "latching", "pumping", "breast milk", "feeding schedule",
            # Hebrew keywords
            "הנקה", "האכלה", "חלב אם", "שאיבת חלב",
            "היצמדות", "אחיזה", "ייצור חלב", "לוח זמני האכלה"
        ]
        self.required_context = [
            "baby_age",
            "feeding_pattern",
            "breastfeeding_challenges",
            "milk_supply",
            "pumping_schedule"
        ]
        self._set_role_boundaries()

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process breastfeeding specific query"""
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
            "feeding_pattern": "What is your current breastfeeding schedule?",
            "breastfeeding_challenges": "Are you experiencing any specific breastfeeding challenges?",
            "milk_supply": "How would you describe your milk supply?",
            "pumping_schedule": "Do you pump? If so, what is your pumping schedule?"
        }
        return questions.get(field, f"Could you tell me about your {field.replace('_', ' ')}?")

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a breastfeeding expert, analyze and respond to: {query}

                  Analysis Framework:
                  1. Feeding Assessment
                     - Age-specific needs
                     - Current patterns
                     - Supply indicators
                     - Latch evaluation
                  
                  2. Challenge Resolution
                     - Common issues
                     - Technique adjustments
                     - Supply management
                     - Comfort measures
                  
                  3. Schedule Optimization
                     - Feeding frequency
                     - Duration guidelines
                     - Night feedings
                     - Pumping integration
                  
                  4. Support Strategy
                     - Position guidance
                     - Supply boosting
                     - Self-care tips
                     - Partner involvement
                  
                  5. Progress Monitoring
                     - Growth indicators
                     - Supply markers
                     - Milestone tracking
                     - When to seek help
                  
                  Important Considerations:
                  - Every mother-baby pair is unique
                  - Focus on overall feeding success
                  - Consider mother's wellbeing
                  - Maintain safety focus
                  
                  Respond in the same language as the question."""

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "breastfeeding guidance",
                "latch techniques",
                "feeding schedules",
                "pumping advice",
                "supply management",
                "common challenges"
            ],
            "cannot_do": [
                "medical diagnosis",
                "medication advice",
                "illness treatment",
                "prescription needs",
                "severe complications"
            ],
            "refer_to": {
                "medical_issues": "pediatrician",
                "severe_pain": "lactation consultant",
                "infections": "healthcare provider",
                "supply_crisis": "lactation specialist",
                "maternal_health": "OB/GYN"
            }
        } 