from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from src.constants import AgentTypes, ResponseTypes, QuestionFields

class SleepRoutineAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.SLEEP_ROUTINE
        self.name = "Sleep Routine Expert"
        self.expertise = [
            # English keywords
            "sleep", "routine", "schedule", "nap", "bedtime", "wake up",
            "sleep training", "daily schedule", "night feeding", "sleep regression",
            "sleep habits", "tired signs", "settling", "self-soothing",
            # Hebrew keywords
            "שינה", "שגרה", "לוח זמנים", "נמנום", "זמן שינה", "התעוררות",
            "אימון שינה", "סדר יום", "האכלת לילה", "רגרסיית שינה",
            "הרגלי שינה", "סימני עייפות", "הרגעה", "הרגעה עצמית"
        ]
        self.required_context = [
            QuestionFields.BABY_AGE,
            QuestionFields.SLEEP_PATTERN
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
        self._set_role_boundaries()

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process sleep routine specific query"""
        try:
            # Get missing critical fields
            missing_fields = self._get_missing_critical_fields(context)
            gathered_info = context.get('gathered_info', {})
            
            # First, try to extract age from the query if we don't have it
            if QuestionFields.BABY_AGE not in gathered_info and "month" in query.lower():
                gathered_info[QuestionFields.BABY_AGE] = query
                context['gathered_info'] = gathered_info
                missing_fields = [f for f in missing_fields if f != QuestionFields.BABY_AGE]
            
            # Then try to extract sleep pattern if we don't have it
            if QuestionFields.SLEEP_PATTERN not in gathered_info and any(word in query.lower() for word in ["hour", "routine", "bath", "pm", "am"]):
                gathered_info[QuestionFields.SLEEP_PATTERN] = query
                context['gathered_info'] = gathered_info
                missing_fields = [f for f in missing_fields if f != QuestionFields.SLEEP_PATTERN]
            
            if missing_fields:
                # If we're missing critical information, ask a follow-up question
                field = missing_fields[0]  # Ask for the first missing field
                return {
                    'type': ResponseTypes.FOLLOW_UP_QUESTION,
                    'text': self._generate_context_question(field)
                }
            
            # If we have all required information, generate a response
            age = gathered_info.get(QuestionFields.BABY_AGE, '')
            sleep_pattern = gathered_info.get(QuestionFields.SLEEP_PATTERN, '')
            
            prompt = f"""Based on this information:
- Baby's age: {age}
- Current sleep pattern/routine: {sleep_pattern}

The parent wants to help their baby fall asleep faster. Provide specific, age-appropriate advice including:
1. A clear step-by-step bedtime routine
2. Optimal timing for sleep (including wake windows)
3. Environmental adjustments
4. Signs of tiredness to watch for
5. Common mistakes to avoid

Keep the response practical and focused."""

            response = await self.llm_service.generate_response(prompt, chat_history)
            
            return {
                'type': ResponseTypes.TEXT,
                'text': response['text']
            }
            
        except Exception as e:
            print(f"Error in sleep routine agent: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': f"Error processing your request: {str(e)}"
            }

    def _generate_context_question(self, field: str) -> str:
        """Generate a context-gathering question for the specified field"""
        questions = {
            QuestionFields.BABY_AGE: "How old is your baby?",
            QuestionFields.SLEEP_PATTERN: "What is your current bedtime routine like? (For example: bath time, feeding, when you start bedtime)",
        }
        return questions.get(field, f"Could you tell me about your baby's {field.replace('_', ' ')}?")

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