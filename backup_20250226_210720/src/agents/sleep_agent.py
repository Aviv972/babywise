from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields, QuestionFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class SleepAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        # Call parent class initialization first
        super().__init__(agent_type, name, llm_service)
        
        # Then set agent-specific attributes
        self.agent_type = AgentTypes.SLEEP
        self.name = "Sleep & Rest Specialist"
        self.required_context = [
            'baby_age', 'current_schedule', 'sleep_environment',
            'sleep_issues', 'sleep_method', 'recent_changes'
        ]
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a comprehensive Sleep & Rest Specialist helping parents establish healthy sleep habits.

Key Areas of Expertise:

1. Sleep Science & Development
   - Age-appropriate sleep needs
   - Sleep cycles and patterns
   - Circadian rhythm development
   - Sleep pressure and timing
   - Sleep associations
   - Biological sleep drives
   - Wake windows by age
   - Total sleep requirements

2. Sleep Environment Optimization
   - Room setup and layout
   - Temperature control (68-72°F/20-22°C)
   - Light management (day vs. night)
   - Sound environment (white noise)
   - Air quality and ventilation
   - Sleep space safety
   - Bedding recommendations
   - Monitoring systems

3. Sleep Schedule Management
   - Wake windows by age
   - Nap transitions and timing
   - Bedtime optimization
   - Night sleep duration
   - Schedule adjustments
   - Routine development
   - Travel adaptations
   - Seasonal changes

4. Sleep Training Methods
   - Age-appropriate approaches
   - Gradual methods
   - Parent presence techniques
   - Cry management strategies
   - Consistency guidelines
   - Progress tracking
   - Method modifications
   - Support strategies

5. Common Sleep Challenges
   - Night wakings
   - Early morning wakings
   - Nap resistance
   - Sleep regressions
   - Developmental transitions
   - Illness adjustments
   - Travel disruptions
   - Environmental changes

6. Sleep Safety Guidelines
   - Safe sleep environment
   - SIDS prevention
   - Sleep position
   - Bedding safety
   - Room sharing guidelines
   - Temperature monitoring
   - Emergency preparedness
   - Risk reduction

Always Consider:
- Baby's exact age and stage
- Current sleep patterns
- Family sleep philosophy
- Cultural preferences
- Living arrangements
- Parental comfort level
- Support system availability
- Medical conditions

Provide:
- Evidence-based recommendations
- Clear implementation steps
- Troubleshooting strategies
- Progress expectations
- Safety guidelines
- Success indicators
- Professional referral criteria
- Follow-up guidance"""),
            ("human", """Query: {query}
Baby's Age: {baby_age}
Current Schedule: {current_schedule}
Sleep Environment: {sleep_environment}
Sleep Issues: {sleep_issues}
Sleep Method: {sleep_method}
Recent Changes: {recent_changes}

Please provide:
1. Age-appropriate sleep assessment
2. Schedule optimization
3. Environment recommendations
4. Method-specific guidance
5. Troubleshooting steps
6. Success indicators
7. Safety reminders""")
        ])

    def get_agent_expertise(self) -> List[str]:
        """Get the agent's areas of expertise."""
        return [
            # Sleep Patterns
            'sleep', 'nap', 'bedtime', 'night', 'wake',
            'schedule', 'routine', 'cycle', 'rhythm',
            'drowsy', 'tired', 'rest', 'awake',
            # Sleep Training
            'sleep training', 'self-soothing', 'settling',
            'crying', 'comfort', 'method', 'technique',
            'ferber', 'extinction', 'gradual', 'gentle',
            # Sleep Environment
            'nursery', 'room', 'temperature', 'light',
            'noise', 'swaddle', 'sleep sack', 'crib',
            'bassinet', 'mattress', 'bedding', 'monitor',
            # Sleep Issues
            'night waking', 'early waking', 'overtired',
            'regression', 'transition', 'separation',
            'teething', 'illness', 'travel', 'daylight',
            # Sleep Safety
            'safe sleep', 'SIDS', 'position', 'bedding',
            'monitoring', 'temperature', 'safety',
            'guidelines', 'recommendations', 'risks'
        ]

    def get_required_fields(self) -> List[str]:
        """Return the required fields for sleep-related queries."""
        return self.required_context

    def get_agent_prompt(self) -> str:
        """Get the agent's system prompt."""
        return f"""You are {self.name}, a specialized baby sleep consultant.
        
        Your expertise covers:
        1. Sleep patterns and schedules
        2. Sleep training methods
        3. Sleep environment optimization
        4. Sleep safety guidelines
        5. Common sleep issues and solutions
        
        Guidelines:
        1. Always consider the baby's age when giving advice
        2. Prioritize safe sleep practices
        3. Be sensitive to different parenting styles
        4. Provide evidence-based recommendations
        5. Explain the reasoning behind your advice
        6. Consider the family's specific circumstances
        7. Maintain consistency with previous advice
        8. Encourage gradual changes when appropriate
        
        Required Information:
        - Baby's age
        - Current sleep schedule
        - Sleep environment details
        - Existing sleep issues
        - Current sleep training method (if any)
        - Recent changes or disruptions
        
        Remember to:
        - Keep safety as the top priority
        - Be empathetic to tired parents
        - Provide practical, actionable steps
        - Acknowledge that every baby is different
        - Recommend consulting a pediatrician when appropriate."""

    def _get_system_prompt(self) -> str:
        return """You are a sleep training specialist focused on helping parents establish healthy sleep routines for their babies.
                 Always consider the baby's age and current schedule when providing advice.
                 If you don't have the baby's age or current sleep schedule, ask for these details first.
                 Be supportive and understanding, acknowledging that sleep training can be challenging.
                 Provide evidence-based advice and explain the reasoning behind your recommendations."""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract sleep-relevant information from conversation history"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        try:
            for message in messages:
                content = message.content.lower()
                
                # Extract age information
                month_patterns = [
                    r'(\d+)[\s-]month[\s-]old',
                    r'(\d+)[\s-]months[\s-]old',
                    r'(\d+)[\s-]month',
                    r'(\d+)[\s-]months'
                ]
                
                for pattern in month_patterns:
                    match = re.search(pattern, content)
                    if match:
                        age_value = int(match.group(1))
                        gathered_info["baby_age"] = {
                            "value": age_value,
                            "unit": "months",
                            "original": f"{age_value} months"
                        }
                        break
                
                # Extract current schedule
                schedule_patterns = {
                    'bedtime': r'(?:bed(?:time)?|night)\s+(?:at|around|by)?\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))',
                    'wake_time': r'(?:wake|up)\s+(?:at|around|by)?\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))',
                    'naps': r'(\d+)\s+naps?(?:\s+a\s+day)?',
                    'wake_windows': r'(?:awake|up)\s+for\s+(\d+(?:\.\d+)?)\s*(?:hour|hr|h|minute|min|m)s?'
                }
                
                for schedule_type, pattern in schedule_patterns.items():
                    match = re.search(pattern, content)
                    if match:
                        if "current_schedule" not in gathered_info:
                            gathered_info["current_schedule"] = {}
                        gathered_info["current_schedule"][schedule_type] = match.group(1)
                
                # Extract sleep environment
                environment_factors = {
                    'temperature': ['temperature', 'hot', 'cold', 'warm', 'cool'],
                    'light': ['light', 'dark', 'bright', 'dim', 'blackout'],
                    'noise': ['noise', 'quiet', 'sound', 'white noise', 'silent'],
                    'sleep_space': ['crib', 'bassinet', 'room', 'nursery', 'bed']
                }
                
                for factor, keywords in environment_factors.items():
                    if any(keyword in content for keyword in keywords):
                        if "sleep_environment" not in gathered_info:
                            gathered_info["sleep_environment"] = {}
                        gathered_info["sleep_environment"][factor] = content
                
                # Extract sleep issues
                sleep_issues = {
                    'night_waking': ['wake', 'waking', 'up', 'night', 'midnight'],
                    'settling': ['settle', 'falling asleep', 'hard to', 'difficult'],
                    'early_waking': ['early', 'morning', 'too early', '5am', '6am'],
                    'nap_issues': ['short nap', 'no nap', 'fight nap', 'resist'],
                    'sleep_regression': ['regression', 'changed', 'suddenly', 'worse']
                }
                
                for issue, keywords in sleep_issues.items():
                    if any(keyword in content for keyword in keywords):
                        if "sleep_issues" not in gathered_info:
                            gathered_info["sleep_issues"] = {}
                        gathered_info["sleep_issues"][issue] = content
                
                # Extract sleep method
                sleep_methods = {
                    'cry_it_out': ['cry it out', 'cio', 'extinction', 'ferber'],
                    'gradual': ['gradual', 'gentle', 'no cry', 'fading'],
                    'chair': ['chair method', 'sleep lady', 'camping out'],
                    'pick_up': ['pick up put down', 'pickup', 'comfort']
                }
                
                for method, keywords in sleep_methods.items():
                    if any(keyword in content for keyword in keywords):
                        gathered_info["sleep_method"] = {
                            'type': method,
                            'description': content
                        }
                
                # Extract recent changes
                change_keywords = ['changed', 'started', 'new', 'different', 'since']
                if any(keyword in content for keyword in change_keywords):
                    if "recent_changes" not in gathered_info:
                        gathered_info["recent_changes"] = []
                    gathered_info["recent_changes"].append(content)
            
            self.logger.info(f"Extracted sleep context: {gathered_info}")
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting sleep context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process sleep-related queries with age-appropriate recommendations"""
        try:
            # First extract context from the current query
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for missing critical information
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "To provide appropriate sleep guidance, I need to know your baby's age and current sleep schedule. Could you share this information?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            result = await self.llm_service.generate_response(
                self.prompt_template.format(
                    query=query,
                    baby_age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                    current_schedule=gathered_info.get("current_schedule", {}),
                    sleep_environment=gathered_info.get("sleep_environment", {}),
                    sleep_issues=gathered_info.get("sleep_issues", {}),
                    sleep_method=gathered_info.get("sleep_method", {}).get("type", "Not specified"),
                    recent_changes=gathered_info.get("recent_changes", [])
                )
            )
            
            # Add age-specific safety reminders
            baby_age = gathered_info.get("baby_age", {}).get("value", 0)
            
            safety_reminder = "\n\nIMPORTANT SAFETY REMINDERS:"
            safety_reminder += "\n- Always place baby on their back to sleep"
            safety_reminder += "\n- Use a firm, flat sleep surface in a crib or bassinet"
            safety_reminder += "\n- Keep soft objects and loose bedding out of the sleep area"
            safety_reminder += "\n- Maintain room temperature between 68-72°F (20-22°C)"
            
            if baby_age < 4:
                safety_reminder += "\n\nFor babies under 4 months:"
                safety_reminder += "\n- Wake for feeding if sleeping more than 4 hours continuously"
                safety_reminder += "\n- Expect irregular sleep patterns"
                safety_reminder += "\n- Do not sleep train at this age"
            elif baby_age < 6:
                safety_reminder += "\n\nFor babies 4-6 months:"
                safety_reminder += "\n- Discuss sleep training with your pediatrician"
                safety_reminder += "\n- Watch for signs of readiness for schedule changes"
            
            result.content += safety_reminder
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in sleep agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your sleep-related question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is sleep-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = [
            'sleep', 'nap', 'bedtime', 'night', 'wake',
            'שינה', 'נמנום', 'שעת שינה', 'לילה', 'ער'
        ]
        
        if any(term in query_lower for term in primary_terms):
            return 1.0
            
        # Secondary domain terms
        secondary_terms = [
            'tired', 'routine', 'schedule', 'drowsy', 'rest',
            'עייף', 'שגרה', 'לוח זמנים', 'מנומנם', 'מנוחה'
        ]
        
        if any(term in query_lower for term in secondary_terms):
            return 0.7
            
        return 0.0

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for sleep advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'current_schedule' not in gathered_info:
            missing.append('current_schedule')
            return missing  # Get schedule next
            
        if 'sleep_environment' not in gathered_info:
            missing.append('sleep_environment')
            
        if 'sleep_issues' not in gathered_info:
            missing.append('sleep_issues')
        
        return missing 