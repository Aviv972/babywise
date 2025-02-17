from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from src.constants import AgentTypes, ResponseTypes, QuestionFields, DynamicFieldDetector

class GeneralAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.GENERAL
        self.name = "General Baby Care Expert"
        self.expertise = [
            # English keywords
            "baby", "care", "general", "advice", "tips", "help",
            "track", "monitor", "app", "tool", "recommend",
            # Hebrew keywords
            "תינוק", "טיפול", "כללי", "עצות", "טיפים", "עזרה",
            "מעקב", "ניטור", "אפליקציה", "כלי", "המלצה"
        ]
        self.required_context = [QuestionFields.BABY_AGE]
        self._set_role_boundaries()
        
        # Define medical disclaimer
        self.medical_disclaimer = (
            "⚠️ Important: I want to clarify that I'm not a medical professional. "
            "This information is for educational purposes only. "
            "For medical advice, diagnosis, or treatment, please consult with your healthcare provider."
        )

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process general baby care queries using dynamic context management"""
        try:
            # Determine query type and required fields dynamically
            field_type = DynamicFieldDetector.extract_field_type(query)
            
            # Emergency queries should be handled immediately
            if self._is_emergency_query(query):
                return {
                    'type': ResponseTypes.TEXT,
                    'text': "For any emergency situation or if your baby is choking, immediately call emergency services (911). While waiting for help, follow these basic first aid steps: [basic steps would be here]. Always prioritize getting professional help in emergency situations."
                }
            
            # Medical queries should be referred to healthcare providers
            if self._is_medical_query(query):
                return {
                    'type': ResponseTypes.TEXT,
                    'text': "For medical concerns, please consult with your pediatrician. They can provide personalized medical advice based on your baby's specific situation and health history."
                }
            
            # Get required fields for this query type
            required_fields = DynamicFieldDetector.get_required_fields(field_type)
            
            # Get current context state
            gathered_info = context.get('gathered_info', {})
            missing_fields = [f for f in required_fields if f not in gathered_info]
            
            # For certain query types, we can provide a general response without age
            if self._can_answer_without_age(query, field_type):
                prompt = await self._generate_field_specific_prompt(field_type, query, context)
                response = await self.llm_service.generate_response(prompt, chat_history)
                return {
                    'type': ResponseTypes.TEXT,
                    'text': response['text']
                }
            
            # If we need more context, ask a follow-up question
            if missing_fields:
                question = self._get_base_question(missing_fields[0])
                if not question:  # Fallback question if base question is not available
                    question = "How old is your baby? This will help me provide age-appropriate advice."
                    
                return {
                    'type': ResponseTypes.FOLLOW_UP_QUESTION,
                    'text': question,
                    'field': missing_fields[0]
                }
            
            # If we have all required information, generate a response
            prompt = await self._generate_field_specific_prompt(field_type, query, context)
            response = await self.llm_service.generate_response(prompt, chat_history)
            
            return {
                'type': ResponseTypes.TEXT,
                'text': response['text'] or "I apologize, but I need more information to provide a helpful response. Could you please provide more details about your question?"
            }
            
        except Exception as e:
            print(f"Error in general agent: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I apologize, but I encountered an error processing your request. Could you please rephrase your question?"
            }

    def _is_emergency_query(self, query: str) -> bool:
        """Check if the query is about an emergency situation"""
        emergency_indicators = [
            'emergency', 'choking', 'breathing', 'accident',
            'hurt', 'injury', 'danger', 'unconscious', 'not breathing'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in emergency_indicators)

    def _can_answer_without_age(self, query: str, field_type: str) -> bool:
        """Determine if we can provide a helpful response without age information"""
        # Topics that don't strictly require age
        age_independent_topics = [
            'safety', 'general', 'product', 'app', 'track',
            'work', 'routine', 'environment'
        ]
        
        # Check if query type is age-independent
        if field_type in age_independent_topics:
            return True
            
        # Check query content
        query_lower = query.lower()
        age_independent_indicators = [
            'app', 'track', 'monitor', 'work', 'job',
            'career', 'routine', 'schedule', 'environment',
            'product', 'buy', 'purchase', 'safety', 'safe'
        ]
        
        return any(indicator in query_lower for indicator in age_independent_indicators)

    def _is_medical_query(self, query: str) -> bool:
        """Check if the query requires medical expertise"""
        medical_indicators = [
            'weight gain', 'growth', 'percentile', 'measurement',
            'fever', 'sick', 'infection', 'disease', 'condition',
            'symptom', 'treatment', 'medicine', 'prescription'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in medical_indicators)

    async def _generate_dynamic_question(self, field: str, field_type: str, original_query: str) -> str:
        """Generate a context-aware follow-up question"""
        prompt = f"""Given:
- Field needed: {field}
- Query type: {field_type}
- Original question: {original_query}

Generate ONE clear, conversational follow-up question to gather the missing information.
The question should:
1. Feel natural in the conversation
2. Be specific to the context
3. Be easy to understand
4. Help provide better advice

Return ONLY the question, no other text."""

        response = await self.llm_service.generate_response(prompt)
        
        # Fallback to base question if LLM fails
        if not response.get('text'):
            return self._get_base_question(field)
            
        return response['text']

    def _get_base_question(self, field: str) -> str:
        """Get a basic follow-up question for a field"""
        base_questions = {
            QuestionFields.BABY_AGE: "How old is your baby? This helps me provide age-appropriate advice.",
            QuestionFields.BABY_WEIGHT: "What is your baby's current weight?",
            QuestionFields.CONCERNS: "What specific concerns do you have?",
            QuestionFields.FEEDING_TYPE: "How are you currently feeding your baby?",
            QuestionFields.SLEEP_PATTERN: "What is your baby's current sleep schedule like?",
            QuestionFields.SYMPTOMS: "What symptoms is your baby experiencing?",
            QuestionFields.PREFERENCES: "Do you have any specific preferences or requirements?",
            QuestionFields.ENVIRONMENT: "Could you describe your baby's environment or situation?"
        }
        return base_questions.get(field, f"Could you tell me more about your baby's {field.replace('_', ' ')}?")

    async def _generate_field_specific_prompt(self, field_type: str, query: str, context: Dict) -> str:
        """Generate a context-aware prompt based on the field type"""
        base_prompt = f"""As a baby care expert, provide advice about: {query}

Consider the following context:
1. Query Type: {field_type}
2. Available Information:
{self._format_gathered_info(context)}

Provide advice that is:
1. Specific and actionable
2. Evidence-based
3. Safety-conscious
4. Easy to implement

If the query requires medical expertise, clearly state that the parent should consult their pediatrician."""
        
        # Let the LLM determine what additional considerations to include
        considerations_prompt = f"""Based on the query type '{field_type}', what specific aspects should be considered in the response?
Return only the key points to consider, no explanations."""
        
        considerations = await self.llm_service.generate_response(considerations_prompt)
        
        return f"{base_prompt}\n\nKey Considerations:\n{considerations['text']}"

    def _format_gathered_info(self, context: Dict) -> str:
        """Format gathered information for prompt"""
        gathered_info = context.get('gathered_info', {})
        if not gathered_info:
            return "No additional context available"
            
        formatted_info = []
        for field, value in gathered_info.items():
            formatted_info.append(f"- {field}: {value}")
        return "\n".join(formatted_info)

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Dynamically determine required fields based on query type"""
        query = context.get('original_query', '')
        field_type = DynamicFieldDetector.extract_field_type(query)
        required_fields = DynamicFieldDetector.get_required_fields(field_type)
        
        gathered_info = context.get('gathered_info', {})
        return [field for field in required_fields if field not in gathered_info]

    def _set_role_boundaries(self):
        """Define what this agent can and cannot do"""
        self.role_boundaries = {
            "can_do": [
                "general baby care advice",
                "daily routine suggestions",
                "product recommendations",
                "app recommendations",
                "basic safety tips",
                "general parenting guidance"
            ],
            "cannot_do": [
                "medical diagnosis",
                "health treatment plans",
                "medication advice",
                "emergency medical guidance",
                "therapy or counseling"
            ],
            "refer_to": {
                "medical_issues": "pediatrician",
                "health_concerns": "healthcare provider",
                "developmental_delays": "child development specialist",
                "mental_health": "child psychologist",
                "emergencies": "emergency services"
            }
        }

    async def process_query(self, query: str, context: Optional[Dict] = None, chat_history: Optional[List[Dict]] = None) -> Dict:
        """Process general parenting queries with enhanced safety checks"""
        try:
            query_lower = query.lower()
            
            # Check if this is a mental health related query
            mental_health_terms = [
                'depression', 'anxiety', 'stress', 'mood', 'emotional', 'feeling',
                'mental', 'therapy', 'postpartum', 'baby blues', 'sad', 'crying',
                'overwhelmed', 'lonely', 'isolated'
            ]
            
            if any(term in query_lower for term in mental_health_terms):
                return await self._handle_mental_health_query(query)
            
            # For other general queries
            prompt = f"""You are a knowledgeable and supportive parenting assistant. 
            Please provide helpful information about: {query}
            
            Remember to:
            1. Be warm and empathetic
            2. Provide clear, practical information
            3. Use simple, easy-to-understand language
            4. Include relevant tips or suggestions
            5. Maintain a supportive tone
            
            If the topic involves health or medical concerns, include appropriate disclaimers."""
            
            response = await self.llm_service.generate_response(prompt)
            
            # Add medical disclaimer if needed
            if self._needs_medical_disclaimer(query):
                response['text'] = f"{self.medical_disclaimer}\n\n{response['text']}"
            
            return {
                'type': ResponseTypes.ANSWER,
                'text': response['text']
            }
            
        except Exception as e:
            print(f"Error in general agent: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I apologize, but I'm having trouble processing your request. Could you please rephrase your question?"
            }

    def _needs_medical_disclaimer(self, query: str) -> bool:
        """Check if the query needs a medical disclaimer"""
        medical_terms = [
            'health', 'medical', 'sick', 'symptoms', 'pain', 'doctor',
            'depression', 'anxiety', 'mental', 'stress', 'postpartum',
            'baby blues', 'medication', 'treatment', 'diagnosis'
        ]
        return any(term in query.lower() for term in medical_terms)

    async def _handle_mental_health_query(self, query: str) -> Dict:
        """Handle mental health related queries with appropriate care"""
        # Start with the medical disclaimer
        response_parts = [self.medical_disclaimer, ""]
        
        if 'baby blues' in query.lower() or 'postpartum depression' in query.lower():
            response_parts.extend([
                "Let me explain the difference between baby blues and postpartum depression:",
                
                "🔹 Baby Blues:",
                "- Very common, affecting up to 80% of new mothers",
                "- Usually starts 2-3 days after delivery",
                "- Typically lasts for a few days up to two weeks",
                "- Symptoms include:",
                "  • Mood swings",
                "  • Crying spells",
                "  • Anxiety",
                "  • Difficulty sleeping",
                "  • Feeling overwhelmed",
                "",
                "🔸 Postpartum Depression (PPD):",
                "- More serious condition affecting about 1 in 7 new mothers",
                "- Can develop anytime within the first year after birth",
                "- Lasts longer than two weeks",
                "- Symptoms include:",
                "  • Persistent sadness or emptiness",
                "  • Loss of interest in activities",
                "  • Changes in sleep and appetite",
                "  • Difficulty bonding with the baby",
                "  • Feelings of worthlessness or guilt",
                "  • Thoughts of harming yourself or the baby",
                "",
                "🚨 Important: If you're experiencing symptoms of postpartum depression, please:",
                "1. Talk to your healthcare provider",
                "2. Reach out to loved ones for support",
                "3. Remember that this is not your fault and help is available",
                "",
                "📞 Resources:",
                "- Postpartum Support International Helpline: 1-800-944-4773",
                "- National Crisis Hotline: 988",
                "- Text 'HOME' to 741741 to connect with a Crisis Counselor"
            ])
        
        return {
            'type': ResponseTypes.ANSWER,
            'text': "\n".join(response_parts)
        }